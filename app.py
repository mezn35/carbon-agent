import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage

# --- 1. SETUP HALAMAN ---
st.set_page_config(page_title="Torajamelo Carbon Auditor", page_icon="⚖️", layout="wide")
st.title("⚖️ Torajamelo Carbon Auditor (Compliance Ready)")
st.caption("Menggunakan Standar DEFRA 2023 & Grid Faktor ESDM Indonesia")

# --- 2. CEK KUNCI ---
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    st.error("🚨 API Key belum disetting!")
    st.stop()

# --- 3. DATABASE EMISI (THE SOURCE OF TRUTH) ---
# Ini adalah "Kitab Suci" data agar akurat.
# Sumber: UK DEFRA 2023 & ESDM Indonesia
FAKTOR_EMISI = {
    # LOGISTIK DARAT (kgCO2e per km per kg muatan tidak relevan, biasanya per km unit)
    # Kita pakai pendekatan: kgCO2e per Ton-KM (Standard Logistics)
    "truk_diesel_kecil": 0.00028, # Van/Small Truck
    "truk_diesel_besar": 0.00008, # Heavy Duty Truck (Lebih efisien per barang)
    "kereta_api_barang": 0.00003, # Sangat rendah
    "mobil_box_bensin": 0.00032,
    
    # LOGISTIK UDARA (Long haul vs Short haul beda)
    "pesawat_domestik": 0.00254, # Jarak pendek < 400km (Boros saat take off)
    "pesawat_internasional": 0.00190, # Jarak jauh > 3000km
    
    # LOGISTIK LAUT
    "kapal_cargo": 0.00001,
    
    # LISTRIK (Grid Emission Factor Indonesia)
    "listrik_jawa_bali": 0.790, # kgCO2e per kWh
    "listrik_sumatera": 0.850,
    "listrik_kalimantan": 1.050, # Masih banyak PLTD
}

# --- 4. DEFINISI ALAT (TOOLS) ---

@tool
def hitung_emisi_logistik_presisi(berat_kg: float, jarak_km: float, jenis_kendaraan: str):
    """
    Menghitung emisi logistik dengan presisi tinggi berdasarkan jenis kendaraan spesifik.
    WAJIB MINTA USER MENJELASKAN JENIS KENDARAAN SECARA SPESIFIK.
    
    Parameters:
    - berat_kg: Berat barang (kg)
    - jarak_km: Jarak tempuh (km)
    - jenis_kendaraan: Pilih salah satu KEY dari database berikut:
      ['truk_diesel_kecil', 'truk_diesel_besar', 'mobil_box_bensin', 'kereta_api_barang', 
       'pesawat_domestik', 'pesawat_internasional', 'kapal_cargo']
    """
    
    # Normalisasi input agar cocok dengan key dictionary
    kunci = jenis_kendaraan.lower().replace(" ", "_")
    
    # Cek ketersediaan data
    if kunci not in FAKTOR_EMISI:
        # Jika AI salah pilih key, kembalikan daftar yang benar
        return f"Error: Jenis kendaraan '{jenis_kendaraan}' tidak spesifik. Pilih dari: {list(FAKTOR_EMISI.keys())}"
    
    faktor = FAKTOR_EMISI[kunci]
    
    # Rumus: Berat (Ton) x Jarak (km) x Faktor (kgCO2e/Ton.km) -> Tapi faktor kita konversi ke kg
    # Faktor di atas adalah per KG per KM untuk penyederhanaan
    total_emisi = berat_kg * jarak_km * faktor
    
    return {
        "status": "SUKSES",
        "metode": "GHG Protocol (Activity Data x Emission Factor)",
        "input": f"{berat_kg}kg x {jarak_km}km via {kunci}",
        "faktor_emisi_ref": f"{faktor} kgCO2e/kg.km (Sumber: DEFRA/Standard)",
        "total_emisi_kgCO2e": round(total_emisi, 4)
    }

@tool
def hitung_emisi_listrik_regional(kwh: float, wilayah: str):
    """
    Menghitung emisi listrik berdasarkan Grid Factor spesifik wilayah di Indonesia.
    Pilihan wilayah: ['listrik_jawa_bali', 'listrik_sumatera', 'listrik_kalimantan']
    """
    kunci = wilayah.lower().replace(" ", "_")
    
    if kunci not in FAKTOR_EMISI:
        # Default ke Jawa Bali jika tidak ketemu
        kunci = "listrik_jawa_bali"
        pesan_tambahan = "(Menggunakan default Grid Jawa-Bali)"
    else:
        pesan_tambahan = ""
        
    faktor = FAKTOR_EMISI[kunci]
    total_emisi = kwh * faktor
    
    return {
        "status": "SUKSES",
        "input": f"{kwh} kWh di {kunci}",
        "faktor_emisi": f"{faktor} kgCO2e/kWh (Sumber: ESDM)",
        "total_emisi_kgCO2e": round(total_emisi, 4),
        "catatan": pesan_tambahan
    }

tools = [hitung_emisi_logistik_presisi, hitung_emisi_listrik_regional]

# --- 5. OTAK AI (AUDITOR PERSONA) ---
llm = ChatGroq(
    temperature=0, # 0 artinya sangat kaku/faktual (bagus untuk auditor)
    model="llama-3.3-70b-versatile", 
    api_key=api_key
).bind_tools(tools)

# --- 6. INTERFACE ---
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Halo. Saya Auditor Karbon Torajamelo. Untuk perhitungan akurat, tolong sebutkan jenis kendaraan spesifik (misal: 'Truk Diesel Kecil' atau 'Pesawat Domestik') dan lokasi listrik (misal: 'Jawa Bali')."}
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Contoh: Kirim 50kg kain dari Jakarta ke Bandung pakai Truk Diesel Kecil"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        # System Prompt yang diubah menjadi AUDITOR TEGAS
        messages_for_ai = [
            SystemMessage(content="""
            Kamu adalah Auditor Penghitung Jejak Karbon Profesional.
            Tugasmu adalah memberikan laporan yang AKURAT untuk pelaporan resmi.
            
            ATURAN:
            1. JANGAN PERNAH MENEBAK. Jika user cuma bilang "naik truk", TANYA BALIK: "Truk jenis apa? Diesel kecil atau besar?".
            2. Gunakan Tools untuk mendapatkan angka pasti.
            3. Jangan gunakan kata "perkiraan" jika sudah menggunakan data Tools. Gunakan kata "Berdasarkan standar DEFRA/ESDM...".
            4. Jika user typo nama kota, koreksi otomatis.
            """)
        ]
        
        for i, m in enumerate(st.session_state.messages):
            if i == 0: continue 
            role_class = HumanMessage if m["role"] == "user" else AIMessage
            messages_for_ai.append(role_class(content=m["content"]))
        
        try:
            response = llm.invoke(messages_for_ai)
            
            if response.tool_calls:
                status_container = st.status("🔍 Mengaudit Data Referensi...", expanded=True)
                tool_messages = []
                
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    status_container.write(f"Query Database: `{tool_name}`")
                    status_container.write(f"Parameter: {tool_args}")
                    
                    selected_tool = {t.name: t for t in tools}[tool_name]
                    tool_output = selected_tool.invoke(tool_args)
                    
                    # Jika output string (error message), tampilkan error
                    if isinstance(tool_output, str) and "Error" in tool_output:
                        status_container.error(tool_output)
                    else:
                        status_container.write("✅ Data ditemukan.")
                    
                    tool_messages.append(ToolMessage(tool_call_id=tool_call["id"], content=str(tool_output)))
                
                status_container.update(label="Audit Selesai", state="complete", expanded=False)

                messages_for_ai.append(response) 
                messages_for_ai.extend(tool_messages)
                messages_for_ai.append(HumanMessage(content="Buatlah laporan formal berdasarkan data angka di atas. Sebutkan sumber datanya (DEFRA/ESDM)."))
                
                final_response = llm.invoke(messages_for_ai)
                st.write(final_response.content)
                st.session_state.messages.append({"role": "assistant", "content": final_response.content})
            
            else:
                # Jika AI tidak pakai tools (biasanya karena user kurang spesifik)
                st.write(response.content)
                st.session_state.messages.append({"role": "assistant", "content": response.content})

        except Exception as e:
            st.error(f"System Error: {str(e)}")
