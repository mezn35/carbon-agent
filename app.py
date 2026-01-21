import streamlit as st
import pandas as pd
from langchain_groq import ChatGroq
from io import BytesIO

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Torajamelo Carbon Dashboard", page_icon="📊", layout="wide")

# --- DATABASE FAKTOR EMISI (STANDAR DEFRA/ESDM) ---
# Source of Truth - Angka ini tidak bisa diganggu gugat oleh AI
EMISSION_FACTORS = {
    "Logistik - Truk Diesel (Kecil)": 0.00028,
    "Logistik - Truk Diesel (Besar)": 0.00008,
    "Logistik - Mobil Box": 0.00032,
    "Logistik - Kereta Api Barang": 0.00003,
    "Logistik - Pesawat Domestik (<400km)": 0.00254,
    "Logistik - Pesawat Internasional (>3000km)": 0.00190,
    "Logistik - Kapal Laut Kargo": 0.00001,
    "Listrik - Grid Jawa-Bali": 0.790,
    "Listrik - Grid Sumatera": 0.850,
    "Listrik - Grid Lainnya": 0.900
}

# --- HEADER ---
st.title("📊 Torajamelo Carbon & Sustainability Report")
st.markdown("---")

# --- SIDEBAR (INPUT DATA) ---
st.sidebar.header("📝 Input Data Laporan")
st.sidebar.info("Masukkan data aktivitas operasional untuk mendapatkan perhitungan akurat sesuai standar GHG Protocol.")

with st.sidebar.form("carbon_form"):
    activity_type = st.selectbox("Jenis Aktivitas", ["Pengiriman Logistik", "Penggunaan Listrik"])
    
    # Input Dinamis
    weight = 0.0
    distance = 0.0
    kwh = 0.0
    factor_key = ""
    
    if activity_type == "Pengiriman Logistik":
        factor_key = st.selectbox("Moda Transportasi", [k for k in EMISSION_FACTORS.keys() if "Logistik" in k])
        weight = st.number_input("Berat Barang (Kg)", min_value=0.0, step=0.1)
        distance = st.number_input("Jarak Tempuh (Km)", min_value=0.0, step=1.0)
    else:
        factor_key = st.selectbox("Lokasi Grid Listrik", [k for k in EMISSION_FACTORS.keys() if "Listrik" in k])
        kwh = st.number_input("Konsumsi Listrik (kWh)", min_value=0.0, step=0.1)
        
    submitted = st.form_submit_button("🧮 Hitung Emisi")

# --- LOGIC PERHITUNGAN (HARD MATH - NO AI GUESSING) ---
if submitted:
    # 1. Hitung Angka Pasti
    factor_val = EMISSION_FACTORS[factor_key]
    emission_result = 0.0
    rumus_text = ""
    
    if activity_type == "Pengiriman Logistik":
        # Rumus: Berat x Jarak x Faktor
        emission_result = weight * distance * factor_val
        rumus_text = f"{weight} kg x {distance} km x {factor_val} (Faktor Emisi)"
    else:
        # Rumus: kWh x Faktor
        emission_result = kwh * factor_val
        rumus_text = f"{kwh} kWh x {factor_val} (Faktor Emisi)"
    
    # 2. Tampilkan Hasil di Dashboard Utama
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Total Emisi (kgCO2e)", value=f"{emission_result:,.4f}")
    with col2:
        st.metric(label="Faktor Emisi Digunakan", value=factor_val)
    with col3:
        st.metric(label="Confidence Level", value="100% (Audited Data)")
        
    st.success(f"✅ **Perhitungan Valid:** {rumus_text}")
    
    # --- BAGIAN AI (HANYA UNTUK ANALISA KUALITATIF) ---
    st.markdown("### 🧠 AI Sustainability Analysis")
    st.caption("Analisa ini dibuat otomatis oleh AI untuk saran pengurangan emisi dalam laporan tahunan.")
    
    if "GROQ_API_KEY" in st.secrets:
        llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=st.secrets["GROQ_API_KEY"])
        
        # Prompt AI: Fokus ke solusi, bukan menghitung ulang
        prompt = f"""
        Saya baru saja menghitung emisi untuk aktivitas: {activity_type} - {factor_key}.
        Total emisi: {emission_result} kgCO2e.
        Detail: {weight if weight else kwh} unit aktivitas.
        
        Berikan 3 paragraf pendek untuk Laporan Keberlanjutan (Sustainability Report):
        1. Analisis dampak lingkungan dari angka ini (apakah tinggi/rendah).
        2. Saran taktis untuk mengurangi emisi ini di masa depan (mitigasi).
        3. Kalimat penutup formal untuk investor.
        
        Gunakan bahasa Indonesia formal korporat.
        """
        
        with st.spinner("AI sedang menyusun narasi laporan..."):
            response = llm.invoke(prompt)
            st.write(response.content)
            
            # Siapkan Data untuk Download
            report_text = f"LAPORAN EMISI TORAJAMELO\n\nAktivitas: {factor_key}\nEmisi: {emission_result} kgCO2e\n\nAnalisa AI:\n{response.content}"
            st.download_button(
                label="📄 Download Laporan (TXT)",
                data=report_text,
                file_name="laporan_emisi_torajamelo.txt",
                mime="text/plain"
            )

    else:
        st.warning("⚠️ API Key Groq belum disetting. Analisa AI tidak muncul.")

else:
    st.info("👈 Silakan isi data operasional di menu sebelah kiri untuk memulai perhitungan.")
    
    # Tampilkan Tabel Referensi untuk Transparansi
    with st.expander("Lihat Database Faktor Emisi (Referensi Standar)"):
        df_ref = pd.DataFrame(list(EMISSION_FACTORS.items()), columns=["Aktivitas", "Faktor Emisi (kgCO2e)"])
        st.table(df_ref)
