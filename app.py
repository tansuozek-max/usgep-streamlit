import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="USGEP Branş Yönlendirme",
    layout="wide"
)

# ---------------------------
# SIDEBAR
# ---------------------------

with st.sidebar:

    logo_yolu = Path(__file__).parent / "logo.png"

    if logo_yolu.exists():
        st.image(str(logo_yolu), width=180)

    st.title("USGEP Menü")

    sayfa = st.radio(
        "Sayfa Seç",
        [
            "🏠 Ana Sayfa",
            "🧒 Sporcu Kayıt",
            "📋 Test Veri Girişi",
            "📊 Sonuçlar",
            "📈 Dashboard"
        ]
    )

# ---------------------------
# ANA SAYFA
# ---------------------------

if sayfa == "🏠 Ana Sayfa":

    st.title("USGEP Branş Yönlendirme Sistemi")

    st.markdown("""
    ### Sistem Durumu

    ✅ Online erişim aktif  
    ✅ Tablet erişimi aktif  
    ✅ Streamlit Cloud yayında  
    ✅ GitHub senkronizasyonu çalışıyor  

    ---
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Tablet", "6")

    with col2:
        st.metric("Branş", "5")

    with col3:
        st.metric("Test Alanı", "17")

# ---------------------------
# SPORCU KAYIT
# ---------------------------

elif sayfa == "🧒 Sporcu Kayıt":

    st.title("Sporcu Kayıt")

    with st.form("sporcu_form"):

        ad = st.text_input("Ad Soyad")
        yas = st.number_input("Yaş", 5, 18)
        cinsiyet = st.selectbox(
            "Cinsiyet",
            ["ERKEK", "KIZ"]
        )

        ilce = st.text_input("İlçe")

        submit = st.form_submit_button("Kaydet")

        if submit:

            yeni_veri = pd.DataFrame([{
                "AD SOYAD": ad,
                "YAŞ": yas,
                "CİNSİYET": cinsiyet,
                "İLÇE": ilce
            }])

            try:
                eski = pd.read_csv("sporcular.csv")
                yeni = pd.concat([eski, yeni_veri], ignore_index=True)

            except:
                yeni = yeni_veri

            yeni.to_csv("sporcular.csv", index=False)

            st.success("Sporcu kaydedildi.")

# ---------------------------
# TEST VERİ GİRİŞİ
# ---------------------------

elif sayfa == "📋 Test Veri Girişi":

    st.title("Test Veri Girişi")

    try:

        sporcular = pd.read_csv("sporcular.csv")

        secili = st.selectbox(
            "Sporcu Seç",
            sporcular["AD SOYAD"]
        )

        st.subheader("Testler")

        boy = st.number_input("Boy")
        kilo = st.number_input("Kilo")
        sprint = st.number_input("20m Sprint")
        dikey = st.number_input("Dikey Sıçrama")

        if st.button("Testleri Kaydet"):

            test_veri = pd.DataFrame([{
                "AD SOYAD": secili,
                "BOY": boy,
                "KİLO": kilo,
                "20M SPRINT": sprint,
                "DİKEY SIÇRAMA": dikey
            }])

            try:
                eski = pd.read_csv("testler.csv")
                yeni = pd.concat([eski, test_veri], ignore_index=True)

            except:
                yeni = test_veri

            yeni.to_csv("testler.csv", index=False)

            st.success("Test verileri kaydedildi.")

    except:
        st.warning("Önce sporcu kaydı oluşturun.")

# ---------------------------
# SONUÇLAR
# ---------------------------

elif sayfa == "📊 Sonuçlar":

    st.title("Sonuçlar")

    try:

        testler = pd.read_csv("testler.csv")

        st.dataframe(
            testler,
            use_container_width=True
        )

    except:
        st.info("Henüz sonuç bulunmuyor.")

# ---------------------------
# DASHBOARD
# ---------------------------

elif sayfa == "📈 Dashboard":

    st.title("Dashboard")

    col1, col2 = st.columns(2)

    try:

        sporcular = pd.read_csv("sporcular.csv")

        with col1:
            st.metric(
                "Toplam Sporcu",
                len(sporcular)
            )

    except:
        with col1:
            st.metric(
                "Toplam Sporcu",
                0
            )

    try:

        testler = pd.read_csv("testler.csv")

        with col2:
            st.metric(
                "Toplam Test",
                len(testler)
            )

    except:
        with col2:
            st.metric(
                "Toplam Test",
                0
            )
