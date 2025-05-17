### ⚙️ Dependency Management: `pip` vs `uv`

You can install dependencies using the standard `pip` or the newer, faster `uv`.

---

#### ✅ Option 1: Using `pip` (Default)

```bash
python -m venv .venv
.venv\Scripts\activate   # On Windows
source .venv/bin/activate  # On Mac/Linux

pip install -r requirements.txt
```

**Pros:**

* Built-in and widely used
* Compatible with all major Python tools and workflows
* Battle-tested across the ecosystem

**Cons:**

* Slower installs
* No built-in lockfile support
* Manual environment setup

---

#### 🚀 Option 2: Using `uv` (Modern & Fast)

```bash
uv venv
.venv\Scripts\Activate.ps1   # On Windows
source .venv/bin/activate    # On Mac/Linux

uv pip install -r requirements.txt
```

**Pros:**

* ⚡ 10–100x faster dependency resolution and installs
* 🛠️ Built-in support for virtualenvs and lockfiles
* 💡 Deterministic installs with `uv pip compile`
* 🧼 Cleaner CLI and simpler workflows

**Cons:**

* Needs separate install (`uv`)
* Slightly newer tool (still gaining adoption)

---

### 📝 Recommendation

We recommend using `uv` for local development and CI pipelines — especially for large or complex Python projects. It’s faster, reproducible, and simplifies environment management.


