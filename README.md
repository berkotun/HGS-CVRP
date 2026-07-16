# HGS-CVRP: Kapasite Kısıtlı Araç Rotalama Problemi için Hibrit Genetik Arama

**Kapasite Kısıtlı Araç Rotalama Problemi (CVRP)** için **Hibrit Genetik Arama (HGS)** metasezgiselinin Python ile gerçeklenmesi. Deneyleri çalıştırmak ve yakınsamayı gerçek zamanlı izlemek için etkileşimli bir **Streamlit** arayüzü içerir.

Vidal ve arkadaşlarının literatürdeki en iyi yöntemlerden biri olan HGS-CVRP algoritmasından esinlenen bu proje; genetik algoritmayı yoğun yerel arama, popülasyon çeşitliliği yönetimi ve uyarlanabilir sarsma (perturbation) ile birleştirerek standart benchmark örneklerinde yüksek kaliteli rotalama çözümleri üretir.

> 2 kişilik üniversite ders projesi olarak geliştirilmiştir. Tüm aşamalar (algoritma tasarımı ve geliştirme, Streamlit arayüzü, benchmark değerlendirmesi) iki üye tarafından ortaklaşa yürütülmüştür.

## Problem

Bir depo, kapasitesi `Q` olan özdeş araçlardan oluşan bir filo ve talepleri ile koordinatları bilinen bir müşteri kümesi verildiğinde, CVRP aşağıdaki koşulları sağlayan en düşük maliyetli rota kümesini arar:

- her rota depodan başlar ve depoda biter,
- her müşteri tam olarak bir kez ziyaret edilir,
- her rotadaki toplam talep, araç kapasitesi `Q`'yu aşamaz.

CVRP NP-zor bir problemdir; kesin (exact) yöntemler gerçekçi boyuttaki örneklere ölçeklenemez. Bu nedenle pratikte HGS gibi metasezgiseller tercih edilir.

## Algoritmaya Genel Bakış

Çözücü, **dev tur (giant tour)** olarak kodlanmış (tüm müşterilerin tek bir permütasyonu) çözümlerden oluşan bir popülasyonu evrimleştirir ve bu turları klasik **Split** algoritmasıyla kapasiteye uygun rotalara ayrıştırır.

| Bileşen | Gerçekleme |
|---|---|
| **Başlangıç popülasyonu** | Üç kurucu sezgiselin karışımı: en yakın komşu ekleme, Clarke–Wright tasarruf algoritması ve süpürme (sweep) algoritması |
| **Rota çözümleme** | Split algoritması (dev turun kapasiteye uygun rotalara optimal bölünmesi; hız için sınırlı pencere) |
| **Ebeveyn seçimi** | İkili turnuva |
| **Çaprazlama** | Dev turlar üzerinde çok parçalı Sıra Çaprazlaması (OX) |
| **Yerel arama** | 3-opt (10 aday yeniden bağlama) + Or-opt (1–3 müşterilik blokların taşınması); uyarlanabilir yoğunlukla uygulanır (hafif / orta / ağır) |
| **Çeşitlilik yönetimi** | Popülasyon maliyet varyansının izlenmesi; çeşitlilik düştüğünde en kötü bireyler rastgele üretilip yeniden iyileştirilen çözümlerle değiştirilir |
| **Sarsma / yeniden başlatma** | Durgunlukla birlikte şiddeti artan uyarlanabilir sarsma (rotalar arası takas ve segment yeniden sıralama), ardından ağır yerel arama |
| **Hayatta kalan seçimi** | Elitist kırpma ile sabit popülasyon boyutu |
| **Durdurma kriterleri** | İterasyon bütçesi veya 3.000 iterasyon boyunca iyileşme olmaması |

Mesafeler Öklid uzaklığıdır ve hız için önbelleğe alınır.

## Arayüz

Streamlit uygulaması şunları sunar:

- çalışma dizinindeki `.vrp` dosyalarının otomatik algılanması,
- ayarlanabilir iterasyon sayısı (1.000–50.000) ve popülasyon boyutu (100–2.000),
- canlı ilerleme: mevcut iterasyon, en iyi maliyet, geçen süre,
- gerçek zamanlı yakınsama grafiği (iterasyona karşı en iyi maliyet) ve sonuç özeti grafiği.

## Benchmark Örnekleri

Depo, 101–153 düğüm aralığında, literatürde yaygın kullanılan **X benchmark kümesinden** (Uchoa vd., 2017) 10 örnek içerir:

`X-n101-k25`, `X-n106-k14`, `X-n110-k13`, `X-n115-k10`, `X-n120-k6`, `X-n125-k30`, `X-n129-k18`, `X-n143-k7`, `X-n148-k46`, `X-n153-k22`

TSPLIB95 `.vrp` formatındaki (`NODE_COORD_SECTION` ve `DEMAND_SECTION` içeren) başka herhangi bir örnek aynı klasöre bırakıldığında dosya seçicide otomatik görünür.

## Kurulum ve Çalıştırma

### Gereksinimler

- Python 3.9+
- `streamlit`, `numpy`, `matplotlib`

```bash
pip install streamlit numpy matplotlib
```

### Çalıştırma

```bash
cd cvrp
streamlit run cvrp.py
```

Ardından açılan tarayıcı sekmesinde: kenar çubuğundan bir `.vrp` örneği seçin, iterasyon sayısı ile popülasyon boyutunu ayarlayın ve **BAŞLAT** düğmesine tıklayın.

## Proje Yapısı

```
.
└── cvrp/
    ├── cvrp.py          # Çözücü (CVRPSolver sınıfı) + Streamlit arayüzü
    └── X-n*.vrp         # Benchmark örnekleri (Uchoa vd. X kümesi)
```

## Kaynaklar

- T. Vidal, *Hybrid Genetic Search for the CVRP: Open-Source Implementation and SWAP\* Neighborhood*, Computers & Operations Research, 2022.
- T. Vidal, T. G. Crainic, M. Gendreau, C. Prins, *A Hybrid Genetic Algorithm with Adaptive Diversity Management for a Large Class of Vehicle Routing Problems with Time-Windows*, 2013.
- C. Prins, *A Simple and Effective Evolutionary Algorithm for the Vehicle Routing Problem*, Computers & Operations Research, 2004.
- E. Uchoa vd., *New Benchmark Instances for the Capacitated Vehicle Routing Problem*, EJOR, 2017.

## Geliştirenler

2 kişilik ders projesi — tüm bileşenler (algoritma, arayüz, değerlendirme) ortaklaşa geliştirilmiştir:

- Berk Ötün
- Meltem Çelik
