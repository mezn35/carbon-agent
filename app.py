import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage

# --- 1. Konfigurasi Halaman ---
st.set_page_config(page_title="Torajamelo Carbon Agent", page_icon="🌱")
st.title("🌱 Torajamelo AI Sustainability Assistant")
st.caption("Powered by Groq (Llama 3.3) & LangChain - 100% Free")

# --- 2. Cek API Key ---
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    st.error("🚨 API Key belum disetting! Masukkan di Settings > Secrets Streamlit.")
    st.stop()

# --- 3. Definisi ALAT (Tools) ---
@tool
def hitung_emisi_logistik(berat_kg: float, jarak_km: float, mode: str):
    """
    Gunakan alat ini untuk menghitung emisi pengiriman barang.
    Parameters:
    - berat_kg: Berat barang dalam Kilogram.
    - jarak_km: WAJIB DIISI. Jika user tidak menyebut angka, KAMU HARUS MENGHITUNG ESTIMASI jarak kasar antar lokasi tersebut dalam KM.
    - mode: Pilih salah satu: 'darat' (truk/mobil), 'udara' (pesawat), atau 'laut' (kapal).
    """
    # Faktor Emisi (kgCO2e per kg-km)
    factors = {
        "darat": 0.0001,  # ~Truck Diesel
        "udara": 0.002,   # ~Air Freight
        "laut": 0.00001   # ~Sea Freight
    }
    selected_factor = factors.get(mode.lower(), 0.0001)
    total_emisi = berat_kg * jarak_km * selected_factor
    
    return {
        "detail": f"Logistik {mode} seberat {berat_kg}kg sejauh {jarak_km}km",
        "total_emisi_kgCO2e": round(total_emisi, 2),
        "pesan": "Perhitungan logistik selesai."
    }

@tool
def hitung_emisi_listrik(kwh: float, lokasi: str = "indonesia"):
    """
    Gunakan alat ini untuk menghitung emisi dari penggunaan listrik.
    """
    factor = 0.79 
    total_emisi = kwh * factor
    return f"Penggunaan {kwh} kWh listrik di {lokasi} menghasilkan estimasi {round(total_emisi, 2)} kgCO2e."

tools = [hitung_emisi_logistik, hitung_emisi_listrik]

# --- 4. Otak AI (LLM Setup) ---
llm = ChatGroq(
    temperature=0, 
    model="llama-3.3-70b-versatile", 
    api_key=api_key
).bind_tools(tools)

# --- 5. Interface Chat & Memory ---
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Halo! Saya siap bantu hitung emisi logistik atau listrik Torajamelo. Silakan tanya!"}
    ]

# Tampilkan history
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Input User
if prompt := st.chat_input("Contoh: Berapa emisi kirim 10kg kain dari Jakarta ke Toraja?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        messages_for_ai = [
            SystemMessage(content="Kamu adalah asisten hitung emisi. Jika kamu menggunakan Tools, WAJIB jelaskan hasil perhitungannya kepada user dalam kalimat lengkap.")
        ]
        
        for i, m in enumerate(st.session_state.messages):
            if i == 0: continue 
            if m["role"] == "user":
                messages_for_ai.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                messages_for_ai.append(AIMessage(content=m["content"]))
        
        try:
            response = llm.invoke(messages_for_ai)
            
            if response.tool_calls:
                status_container = st.status("🤖 Sedang menghitung...", expanded=True)
                tool_messages = []
                
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    status_container.write(f"Mengambil data: `{tool_name}`")
                    status_container.write(f"Parameter: {tool_args}")
                    
                    selected_tool = {t.name: t for t in tools}[tool_name]
                    tool_output = selected_tool.invoke(tool_args)
                    
                    # --- BAGIAN YANG TADI ERROR SUDAH DIPERBAIKI DI BAWAH INI ---
                    tool_messages.append(ToolMessage(tool_call_id=tool_call["id"], content=str(tool_output)))
                    
                    status_container.write("✅ Selesai.")
                
                status_container.update(label="Perhitungan Selesai!", state="complete", expanded=False)

                messages_for_ai.append(response) 
                messages_for_ai.extend(tool_messages)
                messages_for_ai.append(HumanMessage(content="Berdasarkan hasil alat di atas, jelaskan jawabannya kepada saya."))
                
                final_response = llm.invoke(messages_for_ai)
                response_content = final_response.content
            else:
                response_content = response.content

            st.write(response_content)
            st.session_state.messages.append({"role": "assistant", "content": response_content})

        except Exception as e:
            st.error(f"Error: {str(e)}")
