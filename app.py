import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage

# --- 1. SETUP HALAMAN ---
st.set_page_config(page_title="Torajamelo Carbon Auditor", page_icon="⚖️", layout="wide")
st.title("⚖️ Torajamelo Carbon Auditor (Strict Mode)")
st.caption("Menggunakan Standar DEFRA 2023 - Strict Compliance Check")

# --- 2. CEK KUNCI ---
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    st.error("🚨 API Key belum disetting!")
    st.stop()

# --- 3. DATABASE EMISI (THE SOURCE OF TRUTH) ---
# Kita perbanyak variasi agar mengakomodir "Pesawat Boros"
FAKTOR_EMISI = {
    # DARAT
    "truk_diesel_kecil": 0.00028, 
    "truk_diesel_besar": 0.00008,
    "mobil_box": 0.00032,
    "kereta_api": 0.00003,
    
    # UDARA (Logika Boros vs Irit)
    # Short Haul (< 400km) = Sangat Boros (Boros di Takeoff/Landing)
    "pesawat_pendek_boros": 0.00254, 
    # Long Haul (> 3700km) = Lebih Efisien (Cruising phase lama)
    "pesawat_jauh_efisien": 0.00190, 
    
    # LAUT
    "kapal_cargo": 0.00001,
}

# --- 4. DEFINISI ALAT (TOOLS) ---

@tool
def hitung_emisi_logistik_presisi(berat_kg: float, jarak_km: float, jenis_kendaraan: str):
    """
    Menghitung emisi logistik.
    
    CRITICAL RULE:
    Parameter 'jenis_kendaraan' HARUS SAMA PERSIS dengan salah satu key di database:
    ['truk_diesel_kecil', 'truk_diesel_besar', 'mobil_box', 'kereta_api', 
     'pesawat_pendek_boros', 'pesawat_jauh_efisien', 'kapal_cargo']
     
    JIKA USER TIDAK SPESIFIK (misal cuma bilang 'pesawat'), KEMBALIKAN ERROR.
    """
    
    # Normalisasi input
    kunci = jenis_kendaraan.lower().replace(" ", "_")
    
    # --- LOGIC BARU: STRICT VALIDATION ---
    # Jika tidak ada di database, kita TOLAK perhitungannya.
    if kunci not in FAKTOR_EMISI:
        # Kembalikan pesan error ke AI, supaya AI nanya balik ke User
        return (f"GAGAL: Jenis kendaraan '{jenis_kendaraan}' tidak ditemukan di database standar. "
                f"Tanyakan ke user mau pakai yg mana: {list(FAKTOR_EMISI.keys())}")
    
    faktor = FAKTOR_EMISI[kunci]
    total_emisi = berat_kg * jarak_km * faktor
    
    return {
        "status": "VALID",
        "jenis": kunci,
        "input": f"{berat_kg}kg x {jarak_km}km",
        "faktor_emisi": f"{faktor} kgCO2e/kg.km",
        "total_emisi_kgCO2e": round(total_emisi, 4)
    }

tools = [hitung_emisi_logistik_presisi]

# --- 5. OTAK AI (AUDITOR PERSONA) ---
llm = ChatGroq(
    temperature=0, 
    model="llama-3.3-70b-versatile", 
    api_key=api_key
).bind_tools(tools)

# --- 6. INTERFACE ---
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Halo. Saya Auditor Torajamelo. Sebutkan detail pengiriman (Berat, Jarak, Jenis Kendaraan Spesifik)."}
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Contoh: Kirim kain ke Jakarta naik pesawat"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        messages_for_ai = [
            SystemMessage(content="""
            Kamu adalah Auditor Karbon yang SANGAT KAKU dan TELITI.
            
            ATURAN UTAMA:
            1. Jika user bilang "naik pesawat", JANGAN LANGSUNG HITUNG. Coba panggil tool dengan input "pesawat".
            2. Jika tool mengembalikan ERROR/GAGAL, kamu WAJIB bertanya balik ke user untuk memilih opsi yang diberikan tool.
            3. Jangan pernah berasumsi.
            """)
        ]
        
        for i, m in enumerate(st.session_state.messages):
            if i == 0: continue 
            role_class = HumanMessage if m["role"] == "user" else AIMessage
            messages_for_ai.append(role_class(content=m["content"]))
        
        try:
            response = llm.invoke(messages_for_ai)
            
            if response.tool_calls:
                status_container = st.status("🔍 Verifikasi Database...", expanded=True)
                tool_messages = []
                force_stop = False
                
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    status_container.write(f"Cek Spesifikasi: `{tool_args.get('jenis_kendaraan')}`")
                    
                    selected_tool = {t.name: t for t in tools}[tool_name]
                    tool_output = selected_tool.invoke(tool_args)
                    
                    # Cek apakah tool menolak input?
                    if isinstance(tool_output, str) and "GAGAL" in tool_output:
                        status_container.error("❌ Spesifikasi tidak lengkap!")
                        status_container.write("Meminta klarifikasi user...")
                    else:
                        status_container.write("✅ Data Valid.")
                    
                    tool_messages.append(ToolMessage(tool_call_id=tool_call["id"], content=str(tool_output)))
                
                status_container.update(label="Proses Selesai", state="complete", expanded=False)

                messages_for_ai.append(response) 
                messages_for_ai.extend(tool_messages)
                
                final_response = llm.invoke(messages_for_ai)
                st.write(final_response.content)
                st.session_state.messages.append({"role": "assistant", "content": final_response.content})
            
            else:
                st.write(response.content)
                st.session_state.messages.append({"role": "assistant", "content": response.content})

        except Exception as e:
            st.error(f"System Error: {str(e)}")
