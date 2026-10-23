# 🛠️ Utility Scripts Directory

This directory contains maintenance, auditing, manual verification, and database utility scripts for the Trade AI / ApexTrade system.

---

## 📋 Script Inventory

### Auditing & Verification
| Script | Description | Usage |
| :--- | :--- | :--- |
| `audit.py` | Full backend codebase & route audit | `python scripts/audit.py` |
| `hf_audit.py` | Hugging Face space configuration & endpoint audit | `python scripts/hf_audit.py` |
| `verify_security_fixes.py` | Verification suite for cryptographic & session security | `python scripts/verify_security_fixes.py` |
| `test_restart_persistence.py` | Validates database & session persistence across reboots | `python scripts/test_restart_persistence.py` |

### Benchmarks & Testing
| Script | Description | Usage |
| :--- | :--- | :--- |
| `benchmark.py` | Performance and latency benchmarks for calculation routines | `python scripts/benchmark.py` |
| `manual_test_correlation.py` | Manual check for portfolio correlation rejection | `python scripts/manual_test_correlation.py` |
| `test_auth_manual.py` | Manual CLI verification for authentication tokens | `python scripts/test_auth_manual.py` |
| `test_hf_api.py` | Live test runner for Hugging Face endpoints | `python scripts/test_hf_api.py` |
| `test_yfinance_fallback.py` | Validates fallback mechanism when Yahoo Finance feeds timeout | `python scripts/test_yfinance_fallback.py` |
| `test_ws.mjs` | Node.js WebSocket stream test client | `node scripts/test_ws.mjs` |

### Maintenance & Operations
| Script | Description | Usage |
| :--- | :--- | :--- |
| `proxy.bat` | Starts local OpenRouter proxy server (Port 3000) | `.\scripts\proxy.bat` |
| `seed_dummy_data.py` | Populates database with sample instruments and predictions | `python scripts/seed_dummy_data.py` |
| `rotate_jwt_secret.py` | Generates and updates JWT secrets securely | `python scripts/rotate_jwt_secret.py` |
| `risk_engine.py` | Order safety & position sizing engine | Used by trading agent and tests |

### Experimental
- `scripts/experimental/`: Contains work-in-progress test prototypes and research scripts.
