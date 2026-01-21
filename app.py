import streamlit as st
import pandas as pd
from langchain_groq import ChatGroq

# --- 1. KONFIGURASI HALAMAN (LAYOUT PROFESIONAL) ---
st.set_page_config(page_title="Torajamelo GHG Calculator", page_icon="🏛️", layout="wide")

st.title("🏛️ Torajamelo GHG Protocol Calculator")
st.caption("Standardized for POJK 51/2017 & Global Reporting Initiative (GRI)")

# --- 2. DATABASE FAKTOR EMISI (SANGAT DETIL) ---
# Sumber: UK DEFRA 2023, IEA, & ESDM (Grid Indonesia)
# Satuan Faktor disesuaikan dengan input user
FAKTOR_EMISI = {
    # --- SCOPE 2: LISTRIK & MESIN (kgCO2e per kWh) ---
    "Grid Jawa-Bali (PLN)": 0.790,
    "Grid Sumatera (PLN)": 0.850,
    "Grid Kalimantan (PLN)": 1.050,
    "Grid Sulawesi (PLN)": 0.800, # Estimasi wilayah Toraja
    
    # --- SCOPE 3: LOGISTIK (kgCO2e per kg.km) ---
    # Logika: Berat barang mempengaruhi konsumsi BBM kendaraan
    "Logistik - Truk Diesel": 0.00028, 
    "Logistik - Mobil Box (Blind Van)": 0.00032,
    "Logistik - Pesawat Kargo (Domestik)": 0.00254,
    "Logistik - Kapal Laut": 0.00001,
    
    # --- LOGISTIK MIKRO (Spesifik Indonesia) ---
    # Kurir Motor: Emisi per km dibagi asumsi kapasitas angkut rata-rata
    "Kurir Motor (Gojek/Grab) - Dedicated": 0.00018, 
    
    # --- TRANSPORTASI UMUM (Penumpang membawa barang) ---
    # Faktor emisi per penumpang.km (diasumsikan barang = 1 penumpang jika besar)
    "Transport Umum - Bus (TransJakarta)": 0.00010, # Per kg.km (Sangat efisien)
    "Transport Umum - KRL/MRT (Listrik)": 0.00004,  # Per kg.km
}

# --- 3. UI TAB UNTUK SCOPE 1, 2, 3 ---
tab1, tab2, tab3 = st.tabs(["🏭 Scope 2: Mesin & Listrik", "🚚 Scope 3: Logistik & Kurir", "🔥 Scope 1: Genset & BBM"])

# === TAB 1: MESIN PRODUKSI (Packing, Jahit, AC) ===
with tab1:
    st.header("Perhitungan Emisi Listrik & Mesin")
    st.info("Gunakan ini untuk menghitung emisi dari Mesin Packing, Mesin Jahit, Lampu, atau AC.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        nama_mesin = st.text_input("Nama Alat/Mesin", placeholder="Contoh: Mesin Packing A")
        watt_mesin = st.number_input("Daya Listrik (Watt)", min_value=0, value=100, help="Cek label di belakang mesin")
        durasi_jam = st.number_input("Durasi Nyala (Jam)", min_value=0.0, value=1.0)
    with col_b:
        lokasi_grid = st.selectbox("Lokasi Listrik", ["Grid Jawa-Bali (PLN)", "Grid Sulawesi (PLN)", "Grid Sumatera (PLN)"])
    
    if st.button("Hitung Emisi Mesin"):
        # Rumus: (Watt / 1000) * Jam * Faktor Grid
        kwh_used = (watt_mesin / 1000) * durasi_jam
        faktor = FAKTOR_EMISI[lokasi_grid]
        emisi_mesin = kwh_used * faktor
        
        st.success(f"✅ Emisi {nama_mesin}: **{emisi_mesin:.4f} kgCO2e**")
        st.markdown(f"*Detail: {kwh_used:.2f} kWh x {faktor} (Faktor Grid)*")

# === TAB 2: LOGISTIK (Gojek, Truk, KRL) ===
with tab2:
    st.header("Perhitungan Emisi Pengiriman")
    st.info("Mencakup pengiriman bahan baku (Inbound) dan produk jadi ke customer (Outbound).")
    
    col_c, col_d = st.columns(2)
    with col_c:
        moda = st.selectbox("Moda Transportasi", [
            "Kurir Motor (Gojek/Grab) - Dedicated",
            "Transport Umum - Bus (TransJakarta)",
            "Transport Umum - KRL/MRT (Listrik)",
            "Logistik - Mobil Box (Blind Van)",
            "Logistik - Truk Diesel",
            "Logistik - Pesawat Kargo (Domestik)",
            "Logistik - Kapal Laut"
        ])
    with col_d:
        berat_kg = st.number_input("Berat Barang (Kg)", min_value=0.1, value=1.0)
        jarak_km = st.number_input("Jarak Tempuh (Km)", min_value=1.0, value=10.0)
        
    if st.button("Hitung Emisi Logistik"):
        faktor_logistik = FAKTOR_EMISI[moda]
        total_logistik = berat_kg * jarak_km * faktor_logistik
        
        st.success(f"✅ Emisi Pengiriman: **{total_logistik:.4f} kgCO2e**")
        st.markdown(f"*Detail: {berat_kg} kg x {jarak_km} km x {faktor_logistik}*")
        
        # Analisis Cerdas untuk Pemerintah
        if "Pesawat" in moda:
            st.warning("⚠️ **High Emission Alert:** Pengiriman udara memiliki jejak karbon tertinggi. Sarankan opsi laut/darat untuk laporan keberlanjutan.")
        elif "KRL" in moda or "Bus" in moda:
            st.info("🌱 **Green Logistics:** Penggunaan transportasi umum sangat efisien dan bagus untuk nilai ESG perusahaan.")

# === TAB 3: GENSET/BBM (SCOPE 1) ===
with tab3:
    st.header("Perhitungan Bahan Bakar Langsung")
    st.info("Jika pabrik/kantor menggunakan Genset Solar atau kendaraan operasional milik sendiri.")
    
    jenis_bbm = st.selectbox("Jenis Bahan Bakar", ["Solar (Diesel)", "Bensin (Pertalite/Pertamax)", "LPG (Kg)"])
    jumlah_liter = st.number_input("Jumlah Konsumsi (Liter/Kg)", min_value=0.0)
    
    # Faktor Emisi BBM (kgCO2e per Liter) - DEFRA
    FAKTOR_BBM = {
        "Solar (Diesel)": 2.68,
        "Bensin (Pertalite/Pertamax)": 2.31,
        "LPG (Kg)": 2.93
    }
    
    if st.button("Hitung Scope 1"):
        faktor_bbm = FAKTOR_BBM[jenis_bbm]
        emisi_bbm = jumlah_liter * faktor_bbm
        st.success(f"✅ Emisi Langsung: **{emisi_bbm:.4f} kgCO2e**")

# --- FOOTER REPORT GENERATOR ---
st.markdown("---")
st.subheader("📑 Generate Laporan Narasi (AI)")

if "GROQ_API_KEY" in st.secrets:
    if st.button("Buat Analisa Narasi untuk Pemerintah"):
        llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=st.secrets["GROQ_API_KEY"])
        prompt = """
        Buatlah satu paragraf narasi formal untuk Laporan Keberlanjutan (Sustainability Report).
        Konteks: Kami menghitung emisi Scope 1, 2, dan 3 secara terpisah menggunakan standar faktor emisi Grid Indonesia dan DEFRA.
        Tujuan: Menunjukkan transparansi dan akurasi data kepada auditor pemerintah.
        Gunakan bahasa Indonesia baku, profesional, dan meyakinkan.
        """
        with st.spinner("AI menyusun kalimat auditor..."):
            res = llm.invoke(prompt)
            st.write(res.content)
else:
    st.warning("Pasang API Key untuk fitur narasi AI.")
