# 🚀 Load Testing Toolkit

[![k6](https://img.shields.io/badge/k6-7D64FF?style=flat&logo=k6&logoColor=white)](https://k6.io/)
[![Locust](https://img.shields.io/badge/Locust-006600?style=flat&logo=python&logoColor=white)](https://locust.io/)
[![Artillery](https://img.shields.io/badge/Artillery-000000?style=flat&logo=artillery&logoColor=white)](https://artillery.io/)

Koleksi lengkap script load testing menggunakan 3 tools populer: **k6**, **Locust**, dan **Artillery**. Cocok untuk belajar performance testing dari basic sampai advanced.

## 📋 Tentang Project

Project ini berisi script load testing siap pakai untuk menguji REST API. Setiap tool memiliki versi basic dan advanced dengan fitur berbeda.

**Target API untuk Testing:**
- [JSONPlaceholder](https://jsonplaceholder.typicode.com) - REST API dummy untuk testing CRUD
- [ReqRes](https://reqres.in) - API dengan authentication support

## ✨ Fitur

| Feature | k6 | Locust | Artillery |
|---------|:---:|:------:|:---------:|
| Multiple API targets | ✅ | ✅ | ✅ |
| Authentication flow | ✅ | ✅ | ✅ |
| Custom metrics | ✅ | ✅ | ✅ |
| Data-driven testing | ✅ | ✅ | ✅ |
| Parallel requests | ✅ | ✅ | ✅ |
| Custom load shapes | ✅ | ✅ | ✅ |
| Distributed testing | ✅ | ✅ | ✅ |

## 📁 Struktur Project

```
load-testing/
├── k6/
│   ├── script.js              # Basic - CRUD, smoke/load/stress test
│   └── advanced-script.js     # Advanced - Multi-API, auth, 6 scenarios
├── locust/
│   ├── locustfile.py          # Basic - 4 user types, tagged tasks
│   └── advanced_locustfile.py # Advanced - TaskSets, custom load shapes
├── artillery/
│   ├── config.yml             # Basic - 4 scenarios, 5 phases
│   ├── advanced-config.yml    # Advanced - 8 scenarios, CSV data
│   └── data/users.csv         # Test data
└── README.md
```

## 🛠️ Quick Start

### k6 (JavaScript)

```bash
# Install
brew install k6          # macOS
choco install k6         # Windows
sudo apt install k6      # Linux

# Run
k6 run k6/script.js
k6 run k6/advanced-script.js --env SCENARIO=stress
```

### Locust (Python)

```bash
# Install
pip install locust

# Run dengan Web UI (buka http://localhost:8089)
locust -f locust/locustfile.py --host=https://jsonplaceholder.typicode.com

# Headless mode
locust -f locust/locustfile.py --headless -u 100 -r 10 -t 5m
```

### Artillery (Node.js)

```bash
# Install
npm install -g artillery

# Run
artillery run artillery/config.yml

# Generate HTML report
artillery run artillery/config.yml --output report.json
artillery report report.json
```

## 📊 Test Scenarios

Setiap tool mencakup scenario testing berikut:

1. **Smoke Test** - Validasi basic functionality
2. **Load Test** - Simulasi normal traffic
3. **Stress Test** - Push system ke limit
4. **Spike Test** - Sudden traffic surge
5. **Soak Test** - Extended duration test

## 🎯 Use Cases

- Belajar performance testing dari nol
- Template untuk project load testing baru
- Benchmark perbandingan antar tools
- CI/CD integration untuk automated testing

## 📚 Resources

- [k6 Documentation](https://k6.io/docs/)
- [Locust Documentation](https://docs.locust.io/)
- [Artillery Documentation](https://www.artillery.io/docs)

## 📄 License

MIT License - bebas digunakan untuk keperluan apapun.

---

⭐ Star repo ini jika bermanfaat!


## CI/CD Integration

### Konsep

```
Push Code → Build → Deploy Staging → Load Test → Deploy Production
                                         ↓
                                   Pass/Fail Gate
```

### Kapan Test Dijalankan

| Trigger | Test Type | Durasi | Tujuan |
|---------|-----------|--------|--------|
| Pull Request | Smoke | ~1 menit | Quick validation |
| Push to main | Load | ~10 menit | Performance baseline |
| Scheduled (nightly) | Full/Stress | ~1 jam | Regression detection |
| Manual | Any | Varies | Ad-hoc testing |

### GitHub Actions

File: `.github/workflows/load-test.yml`

```bash
# Manual trigger dengan pilihan test type
gh workflow run load-test.yml -f test_type=stress

# Lihat hasil
gh run list --workflow=load-test.yml
```

### GitLab CI

File: `.gitlab-ci.yml`

Setup schedule di GitLab:
1. Go to CI/CD > Schedules
2. Create schedule: `0 2 * * *` (nightly jam 2 pagi)

### Threshold & Gates

Test akan fail jika:
- p95 response time > 500ms
- Error rate > 5%
- Specific checks gagal

Ini mencegah deploy ke production jika performance menurun.

### Best Practices

1. **Smoke test di setiap PR** - Cepat, catch obvious issues
2. **Load test di main branch** - Establish baseline
3. **Stress test scheduled** - Butuh waktu lama, jangan block pipeline
4. **Store results** - Track performance over time
5. **Set realistic thresholds** - Sesuaikan dengan SLA
