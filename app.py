import streamlit as st
import datetime

# --- 1. KONFIGURASI SISTEM AUDIT ---
st.set_page_config(page_title="ESG Auditor System", page_icon="⚖️", layout="wide")

# Styling agar terlihat seperti Software Pemerintah/Enterprise
st.markdown("""
<style>
    .main-header {font-size: 30px; font-weight: bold; color: #2C3E50;}
    .sub-header {font-size: 18px; color: #7F8C8D;}
    .audit-box {background-color: #F8F9F9; padding: 15px; border-radius: 5px; border-left: 5px solid #27AE60;}
    .warning-box {background-color: #FDEDEC; padding: 15px; border-radius: 5px; border-left: 5px solid #E74C3C;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">⚖️ Torajamelo ESG & Carbon Audit System</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Compliance Standard: GHG Protocol Corporate Standard & ISO 14064-1</div>', unsafe_allow_html=True)
st.markdown("---")

# --- 2. DATABASE FAKTOR EMISI (THE SOURCE OF TRUTH) ---
# Data ini diambil dari Laporan Inventarisasi GRK Nasional (Indonesia) & UK DEFRA 2023.
# Struktur Data: {Nama: {Faktor: Angka, Satuan: Unit, Sumber: Referensi}}

DB_EMISI = {
    "SCOPE 1 (Bahan Bakar Langsung)": {
        "Solar/Diesel Industri (B30)": {"faktor": 2.68, "satuan": "kgCO2e/Liter", "sumber": "ESDM & IPCC 2006 (Tier 2)"},
        "Bensin (Ron 90/92)": {"faktor": 2.31, "satuan": "kgCO2e/Liter", "sumber": "IPCC 2006"},
        "LPG (Gas Tabung)": {"faktor": 2.93, "satuan": "kgCO2e/Kg", "sumber": "IPCC 2006"},
    },
    "SCOPE 2 (Listrik & Energi Tidak Langsung)": {
        "Listrik Grid Jawa-Madura-Bali": {"faktor": 0.790, "satuan": "kgCO2e/kWh", "sumber": "Faktor Emisi Grid Jamali 2022 (DJK ESDM)"},
        "Listrik Grid Sumatera": {"faktor": 0.850, "satuan": "kgCO2e/kWh", "sumber": "Faktor Emisi Grid Sumatera 2022"},
        "Listrik Grid Sulawesi (Toraja)": {"faktor": 0.800, "satuan": "kgCO2e/kWh", "sumber": "Estimasi Grid Sulmapa"},
    },
    "SCOPE 3 (Logistik & Rantai Pasok)": {
        # Logistik Darat
        "Truk Diesel Kecil (<3.5 Ton)": {"faktor": 0.00028, "satuan": "kgCO2e/kg.km", "sumber": "UK DEFRA 2023 - HGV Diesel"},
        "Truk Diesel Besar (>7.5 Ton)": {"faktor": 0.00008, "satuan": "kgCO2e/kg.km", "sumber": "UK DEFRA 2023 - HGV Diesel Rigid"},
        "Mobil Box / Blind Van": {"faktor": 0.00032, "satuan": "kgCO2e/kg.km", "sumber": "UK DEFRA 2023 - LCV"},
        "Kurir Motor (Gojek/Grab)": {"faktor": 0.00018, "satuan": "kgCO2e/kg.km", "sumber": "Internal Calculation based on 110cc emission"},
        
        # Logistik Udara (Pembedaan Jarak Sangat Penting)
        "Pesawat Kargo Domestik (<1000km)": {"faktor": 0.00254, "satuan": "kgCO2e/kg.km", "sumber": "UK DEFRA 2023 - Air Freight Short Haul (Inc. RF)"},
        "Pesawat Kargo Internasional": {"faktor": 0.00190, "satuan": "kgCO2e/kg.km", "sumber": "UK DEFRA 2023 - Air Freight Long Haul (Inc. RF)"},
        
        # Logistik Laut
        "Kapal Kargo/Feri": {"faktor": 0.00001, "satuan": "kgCO2e/kg.km", "sumber": "IMO / UK DEFRA 2023"},
        
        # Transportasi Umum (Per Penumpang)
        "Transport Umum: Bus/TransJakarta": {"faktor": 0.10, "satuan": "kgCO2e/pax.km", "sumber": "WRI Indonesia"},
        "Transport Umum: Kereta/KRL": {"faktor": 0.04, "satuan": "kgCO2e/pax.km", "sumber": "KAI Sustainability Report"},
    }
}

# --- 3. INTERFACE INPUT DATA BERBASIS TAB ---
tab1, tab2, tab3, tab4 = st.tabs(["🔥 Scope 1 (BBM)", "⚡ Scope 2 (Listrik)", "🚚 Scope 3 (Logistik)", "📄 Laporan Akhir"])

# ================= SCOPE 1 =================
with tab1:
    st.header("Scope 1: Direct Emissions")
    st.info("Emisi dari pembakaran bahan bakar genset, kendaraan operasional kantor, atau mesin berbahan bakar fosil.")
    
    col1a, col1b = st.columns(2)
    with col1a:
        s1_jenis = st.selectbox("Jenis Bahan Bakar", list(DB_EMISI["SCOPE 1 (Bahan Bakar Langsung)"].keys()))
    with col1b:
        s1_jumlah = st.number_input("Jumlah Konsumsi", min_value=0.0, step=0.1, help="Liter untuk cair, Kg untuk gas")
    
    s1_data = DB_EMISI["SCOPE 1 (Bahan Bakar Langsung)"][s1_jenis]
    
    if s1_jumlah > 0:
        s1_hasil = s1_jumlah * s1_data["faktor"]
        st.markdown(f"""
        <div class="audit-box">
            <b>Hasil Perhitungan Scope 1:</b><br>
            <h3>{s1_hasil:,.4f} kgCO2e</h3>
            <small>Rumus: {s1_jumlah} x {s1_data['faktor']} ({s1_data['satuan']})</small><br>
            <small>Referensi: {s1_data['sumber']}</small>
        </div>
        """, unsafe_allow_html=True)
    else:
        s1_hasil = 0

# ================= SCOPE 2 =================
with tab2:
    st.header("Scope 2: Indirect Energy Emissions")
    st.info("Emisi dari penggunaan listrik PLN untuk kantor, gudang, dan operasional mesin jahit/packing listrik.")
    
    col2a, col2b = st.columns(2)
    with col2a:
        s2_jenis = st.selectbox("Lokasi Grid Listrik", list(DB_EMISI["SCOPE 2 (Listrik & Energi Tidak Langsung)"].keys()))
        # Fitur Detil Mesin
        st.markdown("**Kalkulator Konsumsi Mesin (Opsional)**")
        st.caption("Jika tidak tahu total kWh tagihan, hitung per mesin di sini:")
        m_watt = st.number_input("Watt Mesin", 0)
        m_jam = st.number_input("Durasi Nyala (Jam)", 0.0)
        m_qty = st.number_input("Jumlah Mesin", 1)
        
        kwh_kalkulasi = (m_watt * m_jam * m_qty) / 1000
        if kwh_kalkulasi > 0:
            st.write(f"Estimasi: {kwh_kalkulasi} kWh")
            
    with col2b:
        s2_input_manual = st.number_input("Total Konsumsi Listrik (kWh) dari Tagihan PLN", min_value=0.0, step=0.1)
    
    # Prioritas input: Tagihan PLN > Kalkulasi Mesin
    s2_final_kwh = s2_input_manual if s2_input_manual > 0 else kwh_kalkulasi
    
    s2_data = DB_EMISI["SCOPE 2 (Listrik & Energi Tidak Langsung)"][s2_jenis]
    
    if s2_final_kwh > 0:
        s2_hasil = s2_final_kwh * s2_data["faktor"]
        st.markdown(f"""
        <div class="audit-box">
            <b>Hasil Perhitungan Scope 2:</b><br>
            <h3>{s2_hasil:,.4f} kgCO2e</h3>
            <small>Rumus: {s2_final_kwh:.2f} kWh x {s2_data['faktor']} ({s2_data['satuan']})</small><br>
            <small>Referensi: {s2_data['sumber']}</small>
        </div>
        """, unsafe_allow_html=True)
    else:
        s2_hasil = 0

# ================= SCOPE 3 =================
with tab3:
    st.header("Scope 3: Other Indirect Emissions (Logistics)")
    st.info("Emisi dari pengiriman barang (Inbound/Outbound) menggunakan pihak ketiga (Vendor/Kurir/Pesawat).")
    
    col3a, col3b = st.columns(2)
    with col3a:
        s3_jenis = st.selectbox("Moda Transportasi", list(DB_EMISI["SCOPE 3 (Logistik & Rantai Pasok)"].keys()))
    with col3b:
        # Logika Unit: Jika Transport Umum (Pax), inputnya Orang. Jika Logistik, inputnya Kg.
        if "Transport Umum" in s3_jenis:
            s3_beban = st.number_input("Jumlah Penumpang / Kurir (Orang)", min_value=1, value=1)
            label_beban = "pax"
        else:
            s3_beban = st.number_input("Berat Barang (Gross Weight - Kg)", min_value=0.1, value=1.0)
            label_beban = "kg"
            
        s3_jarak = st.number_input("Jarak Tempuh (KM)", min_value=1.0, value=10.0)

    s3_data = DB_EMISI["SCOPE 3 (Logistik & Rantai Pasok)"][s3_jenis]
    
    # Hitung
    s3_hasil = s3_beban * s3_jarak * s3_data["faktor"]
    
    st.markdown(f"""
    <div class="audit-box">
        <b>Hasil Perhitungan Scope 3:</b><br>
        <h3>{s3_hasil:,.4f} kgCO2e</h3>
        <small>Rumus: {s3_beban} {label_beban} x {s3_jarak} km x {s3_data['faktor']} ({s3_data['satuan']})</small><br>
        <small>Referensi: {s3_data['sumber']}</small>
    </div>
    """, unsafe_allow_html=True)
    
    # Smart Audit Notes (Improvisasi untuk Pemerintah)
    if "Pesawat" in s3_jenis:
        st.markdown("""
        <div class="warning-box">
            <b>⚠️ Audit Note:</b> Penggunaan kargo udara menyumbang emisi tertinggi. 
            Disarankan melampirkan alasan 'Urgency' dalam laporan keberlanjutan jika volume pengiriman udara tinggi.
        </div>
        """, unsafe_allow_html=True)

# ================= LAPORAN AKHIR =================
with tab4:
    st.header("📄 Summary Report Generation")
    
    total_emisi = s1_hasil + s2_hasil + s3_hasil
    
    st.metric("Total Jejak Karbon (Total Carbon Footprint)", f"{total_emisi:,.4f} kgCO2e")
    
    # Generate Text untuk Copy Paste
    tgl = datetime.date.today()
    
    report_text = f"""
    LAPORAN PERHITUNGAN EMISI GRK (GHG REPORT)
    Entitas: Torajamelo
    Tanggal Perhitungan: {tgl}
    Metodologi: GHG Protocol Corporate Standard
    
    RINGKASAN EKSEKUTIF:
    Total Emisi Terhitung: {total_emisi:,.4f} kgCO2e
    
    RINCIAN DATA:
    
    1. SCOPE 1 (Emisi Langsung)
       - Aktivitas: {s1_jenis if s1_jumlah > 0 else "Tidak ada data"}
       - Konsumsi: {s1_jumlah}
       - Total: {s1_hasil:,.4f} kgCO2e
       - Faktor Emisi: {s1_data['faktor']} ({s1_data['sumber']})
       
    2. SCOPE 2 (Emisi Energi)
       - Grid/Lokasi: {s2_jenis}
       - Konsumsi Listrik: {s2_final_kwh:.2f} kWh
       - Total: {s2_hasil:,.4f} kgCO2e
       - Faktor Emisi: {s2_data['faktor']} ({s2_data['sumber']})
       
    3. SCOPE 3 (Emisi Logistik/Lainnya)
       - Moda: {s3_jenis}
       - Beban: {s3_beban} {label_beban}
       - Jarak: {s3_jarak} km
       - Total: {s3_hasil:,.4f} kgCO2e
       - Faktor Emisi: {s3_data['faktor']} ({s3_data['sumber']})
       
    PERNYATAAN:
    Data ini dihitung menggunakan faktor emisi yang diakui secara internasional (DEFRA) dan nasional (ESDM) untuk memastikan kepatuhan pelaporan.
    """
    
    st.text_area("Salin teks ini untuk Laporan Pemerintah/Investor:", report_text, height=400)
    st.download_button("Download Laporan (.txt)", report_text, file_name=f"GHG_Report_Torajamelo_{tgl}.txt")
