import io
import sqlite3
from datetime import datetime
import pandas as pd
from flask import (
    Flask,
    flash,
    redirect,
    render_template_string,
    request,
    send_file,
    url_for,
)

app = Flask(__name__)
app.secret_key = "Burji_group_secret_key"
DB_NAME = "carafat_group.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# Initialize Database Tables
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS account (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            balance REAL DEFAULT 0.0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wadar_trans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            debit_account_id INTEGER,
            credit_account_id INTEGER,
            amount REAL NOT NULL,
            FOREIGN KEY (debit_account_id) REFERENCES account (id),
            FOREIGN KEY (credit_account_id) REFERENCES account (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            qty REAL NOT NULL,
            cost_price REAL NOT NULL,
            selling_price REAL NOT NULL
        )
    """)
    conn.commit()

    # Seed Default Accounts if empty
    cursor.execute("SELECT COUNT(*) FROM account")
    if cursor.fetchone()[0] == 0:
        default_accounts = [
            ("Cash on Hand", "Asset"),
            ("Inventory", "Asset"),
            ("Sales Revenue", "Revenue"),
            ("Purchases Expense", "Expense"),
            ("Operating Expenses", "Expense"),
            ("Other Income", "Revenue"),
            ("Owner's Capital", "Equity"),
            ("Accounts Payable (Deynta)", "Liability"),
        ]
        cursor.executemany(
            "INSERT INTO account (name, type, balance) VALUES (?, ?, 0.0)",
            default_accounts,
        )
        conn.commit()
    conn.close()


init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="so" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <title>Burji Group - Professional Accounting System</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        function showSection(sectionId) {
            document.querySelectorAll('.content-section').forEach(sec => sec.classList.add('hidden'));
            const welcomeMsg = document.getElementById('welcome-message');
            if (welcomeMsg) welcomeMsg.classList.add('hidden');
            const activeSec = document.getElementById(sectionId);
            if (activeSec) activeSec.classList.remove('hidden');
        }
        function toggleForm(formId) {
            const form = document.getElementById(formId);
            form.classList.toggle('hidden');
        }
    </script>
</head>
<body class="bg-[#0f172a] text-gray-100 font-sans flex h-screen overflow-hidden">

    <!-- Sidebar Menu -->
    <div class="w-64 bg-[#090d16] border-r border-gray-800 flex flex-col shadow-2xl overflow-y-auto">
        <div class="p-6 text-center border-b border-gray-800 bg-[#06090f]">
            <h2 class="text-xl font-black tracking-wide text-emerald-400">🛒 Burji Group</h2>
            <p class="text-[10px] text-gray-400 uppercase mt-1 tracking-wider font-semibold">Management System</p>
        </div>
        <nav class="flex flex-col gap-1 p-3 text-sm">
            <button onclick="showSection('section-dashboard')" class="text-left px-4 py-3 rounded-xl hover:bg-emerald-600 hover:text-white transition font-medium flex items-center gap-3 text-gray-300">📊 Dashboard</button>
            <button onclick="showSection('section-reports')" class="text-left px-4 py-3 rounded-xl hover:bg-emerald-600 hover:text-white transition font-medium flex items-center gap-3 text-gray-300">📈 Reports (Balance Sheet)</button>
            <button onclick="showSection('section-inventory')" class="text-left px-4 py-3 rounded-xl hover:bg-emerald-600 hover:text-white transition font-medium flex items-center gap-3 text-gray-300">📦 Inventory</button>
            <button onclick="showSection('section-sales')" class="text-left px-4 py-3 rounded-xl hover:bg-emerald-600 hover:text-white transition font-medium flex items-center gap-3 text-gray-300">🛒 Sales (Revenue)</button>
            <button onclick="showSection('section-purchases')" class="text-left px-4 py-3 rounded-xl hover:bg-emerald-600 hover:text-white transition font-medium flex items-center gap-3 text-gray-300">🛍️ Purchases</button>
            <button onclick="showSection('section-income')" class="text-left px-4 py-3 rounded-xl hover:bg-emerald-600 hover:text-white transition font-medium flex items-center gap-3 text-gray-300">💵 Other Income</button>
            <button onclick="showSection('section-expenses')" class="text-left px-4 py-3 rounded-xl hover:bg-emerald-600 hover:text-white transition font-medium flex items-center gap-3 text-gray-300">📉 Expenses</button>
            <button onclick="showSection('section-opening')" class="text-left px-4 py-3 rounded-xl hover:bg-emerald-600 hover:text-white transition font-medium flex items-center gap-3 text-yellow-400">⭐ Start Up Balance</button>
            <button onclick="showSection('section-journal')" class="text-left px-4 py-3 rounded-xl hover:bg-emerald-600 hover:text-white transition font-medium flex items-center gap-3 text-gray-300">📑 Journal Entries</button>
        </nav>
    </div>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col overflow-y-auto bg-[#0b1120]">
        <header class="bg-[#0f172a] border-b border-gray-800 px-8 py-4 flex justify-between items-center shadow-md">
            <div class="flex items-center gap-4">
                <h1 class="text-lg font-bold text-gray-200">Double-Entry Accounting & Inventory</h1>
                <button id="install-btn" style="display: none;" class="bg-emerald-500 text-white px-3 py-1.5 rounded-xl text-xs font-bold shadow-lg hover:bg-emerald-600 transition items-center gap-1.5">
                    📲 Ku rakib App-ka
                </button>
            </div>
            <div class="bg-emerald-950 border border-emerald-800 px-5 py-2 rounded-xl shadow-inner flex items-center gap-4">
                <span class="text-gray-300 text-xs font-semibold uppercase">Cash on Hand:</span>
                <span class="text-xl font-black text-emerald-400">${{ cash_balance }}</span>
            </div>
        </header>

        <div class="p-8 space-y-6">

            <!-- Welcome Message -->
            <div id="welcome-message" class="bg-[#1e293b] border border-gray-800 p-16 rounded-2xl shadow-xl text-center text-gray-400">
                <h2 class="text-2xl font-bold text-white mb-2">Soo Dhawoow Burji Group!</h2>
                <p class="text-sm">Dooro qayb ka mid ah liiska bidix si aad u maamusho nidaamka.</p>
            </div>

            <!-- Dashboard Section -->
            <div id="section-dashboard" class="content-section hidden space-y-6">
                <h3 class="text-xl font-bold text-white">Business Overview</h3>
                <div class="grid grid-cols-3 gap-6">
                    <div class="bg-[#1e293b] border border-gray-800 p-6 rounded-2xl shadow-lg border-t-4 border-t-emerald-500">
                        <h4 class="text-gray-400 text-xs font-bold uppercase tracking-wider">Total Revenue</h4>
                        <p class="text-3xl font-black text-emerald-400 mt-2">${{ total_revenue }}</p>
                    </div>
                    <div class="bg-[#1e293b] border border-gray-800 p-6 rounded-2xl shadow-lg border-t-4 border-t-red-500">
                        <h4 class="text-gray-400 text-xs font-bold uppercase tracking-wider">Total Expenses</h4>
                        <p class="text-3xl font-black text-red-400 mt-2">${{ total_expenses }}</p>
                    </div>
                    <div class="bg-[#1e293b] border border-gray-800 p-6 rounded-2xl shadow-lg border-t-4 border-t-blue-500">
                        <h4 class="text-gray-400 text-xs font-bold uppercase tracking-wider">Net Profit / Loss</h4>
                        <p class="text-3xl font-black text-blue-400 mt-2">${{ net_profit }}</p>
                    </div>
                </div>
            </div>

            <!-- Reports Section -->
            <div id="section-reports" class="content-section hidden bg-[#1e293b] border border-gray-800 p-6 rounded-2xl shadow-lg">
                <h3 class="text-xl font-bold text-white mb-4">Balance Sheet & Accounts Report</h3>
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-[#0f172a] text-gray-400 text-xs uppercase tracking-wider"><th class="p-3 border-b border-gray-800">Account Name</th><th class="p-3 border-b border-gray-800">Type</th><th class="p-3 border-b border-gray-800">Balance</th></tr>
                    </thead>
                    <tbody class="divide-y divide-gray-800 text-sm">
                        {% for acc in accounts %}
                        <tr>
                            <td class="p-3 font-semibold text-gray-200">{{ acc.name }}</td>
                            <td class="p-3 text-gray-400">{{ acc.type }}</td>
                            <td class="p-3 font-bold text-emerald-400">${{ acc.balance }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>

            <!-- Inventory Section -->
            <div id="section-inventory" class="content-section hidden bg-[#1e293b] border border-gray-800 p-6 rounded-2xl shadow-lg">
                <div class="flex justify-between items-center mb-6">
                    <h3 class="text-xl font-bold text-emerald-400">Inventory (Alaabta Kaydka)</h3>
                    <div class="flex gap-2">
                        <a href="/export_inventory_excel" class="bg-blue-600 text-white px-4 py-2 rounded-xl hover:bg-blue-700 text-xs font-semibold transition">Export Excel (.xlsx)</a>
                        <button onclick="toggleForm('form-inventory')" class="bg-emerald-600 text-white px-4 py-2 rounded-xl hover:bg-emerald-700 text-xs font-semibold transition">+ Ku dar Alaab</button>
                    </div>
                </div>

                <form action="/import_inventory" method="POST" enctype="multipart/form-data" class="bg-[#0f172a] border border-gray-800 p-4 rounded-xl mb-6 flex items-center justify-between">
                    <div class="flex items-center gap-3 w-full">
                        <label class="text-xs font-semibold text-gray-300 whitespace-nowrap uppercase">Import Excel:</label>
                        <input type="file" name="file" accept=".xlsx" class="border border-gray-700 p-2 rounded-xl w-full bg-[#1e293b] text-sm text-gray-300" required>
                        <button type="submit" class="bg-indigo-600 text-white px-5 py-2 rounded-xl hover:bg-indigo-700 text-xs font-semibold transition">Upload</button>
                    </div>
                </form>

                <table class="w-full text-left border-collapse mb-6">
                    <thead>
                        <tr class="bg-[#0f172a] text-gray-400 text-xs uppercase tracking-wider">
                            <th class="p-3 border-b border-gray-800">ID</th>
                            <th class="p-3 border-b border-gray-800">Item Name</th>
                            <th class="p-3 border-b border-gray-800">Tirada</th>
                            <th class="p-3 border-b border-gray-800">Cost Price</th>
                            <th class="p-3 border-b border-gray-800">Selling Price</th>
                            <th class="p-3 border-b border-gray-800">Tallaabooyinka</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-800 text-sm">
                        {% for i in inventory %}
                        <tr>
                            <td class="p-3 text-gray-400">{{ i.id }}</td>
                            <td class="p-3 font-semibold text-white">{{ i.item }}</td>
                            <td class="p-3 text-gray-300">{{ i.qty }}</td>
                            <td class="p-3 text-gray-300">${{ i.cost_price }}</td>
                            <td class="p-3 text-emerald-400 font-bold">${{ i.selling_price }}</td>
                            <td class="p-3 flex gap-2">
                                <button onclick="toggleForm('form-update-{{ i.id }}')" class="bg-blue-600 text-white px-3 py-1 rounded-lg text-xs hover:bg-blue-700 transition">Baddel</button>
                                <form action="/delete_inventory/{{ i.id }}" method="POST" class="inline">
                                    <button type="submit" class="bg-red-600 text-white px-3 py-1 rounded-lg text-xs hover:bg-red-700 transition" onclick="return confirm('Ma hubtaa inaad tirtirto alaabtan?')">Tirtir</button>
                                </form>
                            </td>
                        </tr>
                        <tr id="form-update-{{ i.id }}" class="hidden bg-[#0f172a]">
                            <td colspan="6" class="p-4">
                                <form action="/update_inventory/{{ i.id }}" method="POST" class="flex gap-3 items-center">
                                    <input type="text" name="item" value="{{ i.item }}" class="border border-gray-700 p-2 rounded-xl w-1/4 bg-[#1e293b] text-sm text-white" required>
                                    <input type="number" step="any" name="qty" value="{{ i.qty }}" class="border border-gray-700 p-2 rounded-xl w-1/4 bg-[#1e293b] text-sm text-white" required>
                                    <input type="number" step="any" name="cost_price" value="{{ i.cost_price }}" class="border border-gray-700 p-2 rounded-xl w-1/4 bg-[#1e293b] text-sm text-white" required>
                                    <input type="number" step="any" name="selling_price" value="{{ i.selling_price }}" class="border border-gray-700 p-2 rounded-xl w-1/4 bg-[#1e293b] text-sm text-white" required>
                                    <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded-xl text-xs font-semibold">Keydi</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                <form id="form-inventory" action="/add_inventory" method="POST" class="flex gap-3 hidden mt-4 pt-4 border-t border-gray-800">
                    <input type="text" name="item" placeholder="Item Name" class="border border-gray-700 p-2.5 rounded-xl w-1/4 text-sm bg-[#0f172a] text-white" required>
                    <input type="number" step="any" name="qty" placeholder="Tirada" class="border border-gray-700 p-2.5 rounded-xl w-1/4 text-sm bg-[#0f172a] text-white" required>
                    <input type="number" step="any" name="cost_price" placeholder="Cost Price" class="border border-gray-700 p-2.5 rounded-xl w-1/4 text-sm bg-[#0f172a] text-white" required>
                    <input type="number" step="any" name="selling_price" placeholder="Selling Price" class="border border-gray-700 p-2.5 rounded-xl w-1/4 text-sm bg-[#0f172a] text-white" required>
                    <button type="submit" class="bg-emerald-600 text-white px-6 py-2.5 rounded-xl text-xs font-semibold hover:bg-emerald-700">Keydi</button>
                </form>
            </div>

            <!-- Sales Section (Dropdown & Automatic Inventory Deduction) -->
            <div id="section-sales" class="content-section hidden bg-[#1e293b] border border-gray-800 p-6 rounded-2xl shadow-lg">
                <div class="flex justify-between items-center mb-6">
                    <h3 class="text-xl font-bold text-purple-400">Sales Orders (Iibinta - Dakhli)</h3>
                    <button onclick="toggleForm('form-sales')" class="bg-purple-600 text-white px-4 py-2 rounded-xl hover:bg-purple-700 text-xs font-semibold transition">+ Diiwaangeli Iib</button>
                </div>
                <form id="form-sales" action="/add_sale" method="POST" class="flex flex-col gap-4 hidden mt-4 mb-6 pt-4 border-t border-gray-800">
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-xs font-semibold text-gray-400 uppercase mb-1">Taariikhda</label>
                            <input type="date" name="transaction_date" class="border border-gray-700 p-2.5 rounded-xl w-full text-sm bg-[#0f172a] text-white" required>
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-gray-400 uppercase mb-1">Dooro Alaabta (Kaydka)</label>
                            <select name="inventory_id" class="border border-gray-700 p-2.5 rounded-xl w-full text-sm bg-[#0f172a] text-white" required>
                                <option value="">-- Dooro Alaab --</option>
                                {% for i in inventory %}
                                <option value="{{ i.id }}">{{ i.item }} (Kaydka: {{ i.qty }} - Qiimaha: ${{ i.selling_price }})</option>
                                {% endfor %}
                            </select>
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-xs font-semibold text-gray-400 uppercase mb-1">Tirada la Iibinayo</label>
                            <input type="number" step="any" name="quantity" placeholder="Tirada" class="border border-gray-700 p-2.5 rounded-xl w-full text-sm bg-[#0f172a] text-white" required>
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-gray-400 uppercase mb-1">Wadarta Lacagta ($)</label>
                            <input type="number" step="any" name="amount" placeholder="Wadarta Guud ($)" class="border border-gray-700 p-2.5 rounded-xl w-full text-sm bg-[#0f172a] text-white" required>
                        </div>
                    </div>
                    <div>
                        <input type="text" name="description" placeholder="Faahfaahinta Iibka (Tusaale: Iibinta alaab)" class="border border-gray-700 p-2.5 rounded-xl w-full text-sm bg-[#0f172a] text-white" required>
                    </div>
                    <div>
                        <button type="submit" class="bg-purple-600 text-white px-6 py-2.5 rounded-xl text-xs font-semibold hover:bg-purple-700">Diiwaangeli Iibka</button>
                    </div>
                </form>
            </div>

            <!-- Purchases Section -->
            <div id="section-purchases" class="content-section hidden bg-[#1e293b] border border-gray-800 p-6 rounded-2xl shadow-lg">
                <div class="flex justify-between items-center mb-6">
                    <h3 class="text-xl font-bold text-indigo-400">Purchases (Iibsashada Alaabta)</h3>
                    <button onclick="toggleForm('form-purchases')" class="bg-indigo-600 text-white px-4 py-2 rounded-xl hover:bg-indigo-700 text-xs font-semibold transition">+ Diiwaangeli Iibsasho</button>
                </div>
                <form id="form-purchases" action="/add_purchase" method="POST" class="flex gap-3 hidden mt-4 mb-6 pt-4 border-t border-gray-800">
                    <input type="date" name="transaction_date" class="border border-gray-700 p-2.5 rounded-xl text-sm bg-[#0f172a] text-white" required>
                    <input type="text" name="description" placeholder="Faahfaahinta iibsashada" class="border border-gray-700 p-2.5 rounded-xl w-1/3 text-sm bg-[#0f172a] text-white" required>
                    <input type="number" step="any" name="amount" placeholder="Kharashka ($)" class="border border-gray-700 p-2.5 rounded-xl w-1/4 text-sm bg-[#0f172a] text-white" required>
                    <button type="submit" class="bg-indigo-600 text-white px-6 py-2.5 rounded-xl text-xs font-semibold hover:bg-indigo-700">Diiwaangeli</button>
                </form>
            </div>

            <!-- Other Income Section -->
            <div id="section-income" class="content-section hidden bg-[#1e293b] border border-gray-800 p-6 rounded-2xl shadow-lg">
                <div class="flex justify-between items-center mb-6">
                    <h3 class="text-xl font-bold text-green-400">Other Income (Dakhli Kale)</h3>
                    <button onclick="toggleForm('form-income')" class="bg-green-600 text-white px-4 py-2 rounded-xl hover:bg-green-700 text-xs font-semibold transition">+ Ku dar Dakhli</button>
                </div>
                <form id="form-income" action="/add_income" method="POST" class="flex gap-3 hidden mt-4 mb-6 pt-4 border-t border-gray-800">
                    <input type="date" name="transaction_date" class="border border-gray-700 p-2.5 rounded-xl text-sm bg-[#0f172a] text-white" required>
                    <input type="text" name="description" placeholder="Xaggee ka imid" class="border border-gray-700 p-2.5 rounded-xl w-1/3 text-sm bg-[#0f172a] text-white" required>
                    <input type="number" step="any" name="amount" placeholder="Lacagta ($)" class="border border-gray-700 p-2.5 rounded-xl w-1/4 text-sm bg-[#0f172a] text-white" required>
                    <button type="submit" class="bg-green-600 text-white px-6 py-2.5 rounded-xl text-xs font-semibold hover:bg-green-700">Diiwaangeli</button>
                </form>
            </div>

            <!-- Expenses Section -->
            <div id="section-expenses" class="content-section hidden bg-[#1e293b] border border-gray-800 p-6 rounded-2xl shadow-lg">
                <div class="flex justify-between items-center mb-6">
                    <h3 class="text-xl font-bold text-red-400">Expenses (Kharashaadka Guud)</h3>
                    <button onclick="toggleForm('form-expenses')" class="bg-red-600 text-white px-4 py-2 rounded-xl hover:bg-red-700 text-xs font-semibold transition">+ Ku dar Kharash</button>
                </div>
                <form id="form-expenses" action="/add_expense" method="POST" class="flex gap-3 hidden mt-4 mb-6 pt-4 border-t border-gray-800">
                    <input type="date" name="transaction_date" class="border border-gray-700 p-2.5 rounded-xl text-sm bg-[#0f172a] text-white" required>
                    <input type="text" name="description" placeholder="Sababta Kharashka" class="border border-gray-700 p-2.5 rounded-xl w-1/3 text-sm bg-[#0f172a] text-white" required>
                    <input type="number" step="any" name="amount" placeholder="Lacagta ($)" class="border border-gray-700 p-2.5 rounded-xl w-1/4 text-sm bg-[#0f172a] text-white" required>
                    <button type="submit" class="bg-red-600 text-white px-6 py-2.5 rounded-xl text-xs font-semibold hover:bg-red-700">Diiwaangeli</button>
                </form>
            </div>

            <!-- Start Up Balance Section -->
            <div id="section-opening" class="content-section hidden bg-[#1e293b] border border-gray-800 p-6 rounded-2xl shadow-lg">
                <div class="mb-4">
                    <h3 class="text-xl font-bold text-yellow-400">Start Up Balance (Hadhaaga Bilowga ah)</h3>
                    <p class="text-xs text-gray-400 mt-1">Halkan ku diiwaangeli hantida ama lacagta aad ku furtay ganacsiga.</p>
                </div>
                <form action="/add_opening_balance" method="POST" class="space-y-4 pt-4 border-t border-gray-800">
                    <div class="grid grid-cols-3 gap-4">
                        <div>
                            <label class="block text-gray-300 text-xs font-bold uppercase tracking-wider mb-2">Taariikhda</label>
                            <input type="date" name="transaction_date" class="border border-gray-700 p-2.5 rounded-xl w-full text-sm bg-[#0f172a] text-white" required>
                        </div>
                        <div>
                            <label class="block text-gray-300 text-xs font-bold uppercase tracking-wider mb-2">Account-ka Hantida (Debit)</label>
                            <select name="debit_account" class="border border-gray-700 p-2.5 rounded-xl w-full text-sm bg-[#0f172a] text-white" required>
                                <option value="Cash on Hand">Cash on Hand (Lacagta Gacanta)</option>
                                <option value="Inventory">Inventory (Alaabta Kaydka)</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-gray-300 text-xs font-bold uppercase tracking-wider mb-2">Capital Account (Credit)</label>
                            <input type="text" value="Owner's Capital" class="border border-gray-700 p-2.5 rounded-xl w-full bg-[#0f172a] text-gray-400 text-sm" disabled>
                        </div>
                    </div>
                    <div class="flex gap-4 items-end">
                        <input type="text" name="description" placeholder="Faahfaahinta (Tusaale: Starting Capital)" class="border border-gray-700 p-2.5 rounded-xl w-1/2 text-sm bg-[#0f172a] text-white" required>
                        <input type="number" step="any" name="amount" placeholder="Wadarta Lacagta ($)" class="border border-gray-700 p-2.5 rounded-xl w-1/3 text-sm bg-[#0f172a] text-white" required>
                        <button type="submit" class="bg-yellow-600 text-white px-6 py-2.5 rounded-xl text-xs font-semibold hover:bg-yellow-700 transition">Diiwaangeli</button>
                    </div>
                </form>
            </div>

            <!-- Journal Entries Section -->
            <div id="section-journal" class="content-section hidden bg-[#1e293b] border border-gray-800 p-6 rounded-2xl shadow-lg space-y-6">
                <div class="flex justify-between items-center">
                    <h3 class="text-xl font-bold text-white">General Journal (Diiwaanka Xisaabaadka)</h3>
                    <button onclick="toggleForm('form-manual-journal')" class="bg-emerald-600 text-white px-4 py-2 rounded-xl hover:bg-emerald-700 text-xs font-semibold transition">+ Ku dar Journal Cusub</button>
                </div>

                <form id="form-manual-journal" action="/add_manual_journal" method="POST" class="bg-[#0f172a] border border-gray-800 p-5 rounded-xl hidden space-y-4">
                    <h4 class="font-bold text-gray-300 text-xs uppercase tracking-wider">Diiwaangeli Transaction (Debit & Credit)</h4>
                    <div class="grid grid-cols-3 gap-4">
                        <div>
                            <label class="block text-xs font-semibold text-gray-400 uppercase mb-1">Taariikhda</label>
                            <input type="date" name="transaction_date" class="border border-gray-700 p-2.5 rounded-xl w-full bg-[#1e293b] text-sm text-white" required>
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-gray-400 uppercase mb-1">Debit Account</label>
                            <select name="debit_account" class="border border-gray-700 p-2.5 rounded-xl w-full bg-[#1e293b] text-sm text-white" required>
                                {% for acc in accounts %}
                                <option value="{{ acc.name }}">{{ acc.name }} ({{ acc.type }})</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-gray-400 uppercase mb-1">Credit Account</label>
                            <select name="credit_account" class="border border-gray-700 p-2.5 rounded-xl w-full bg-[#1e293b] text-sm text-white" required>
                                {% for acc in accounts %}
                                <option value="{{ acc.name }}">{{ acc.name }} ({{ acc.type }})</option>
                                {% endfor %}
                            </select>
                        </div>
                    </div>
                    <div class="flex gap-4">
                        <input type="text" name="description" placeholder="Faahfaahinta (Tusaale: Deynta Rikaab)" class="border border-gray-700 p-2.5 rounded-xl w-1/2 bg-[#1e293b] text-sm text-white" required>
                        <input type="number" step="any" name="amount" placeholder="Wadarta Lacagta ($)" class="border border-gray-700 p-2.5 rounded-xl w-1/3 bg-[#1e293b] text-sm text-white" required>
                        <button type="submit" class="bg-emerald-600 text-white px-6 py-2.5 rounded-xl text-xs font-semibold hover:bg-emerald-700">Kaydi</button>
                    </div>
                </form>

                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-[#0f172a] text-gray-400 text-xs uppercase tracking-wider"><th class="p-3 border-b border-gray-800">ID</th><th class="p-3 border-b border-gray-800">Taariikhda</th><th class="p-3 border-b border-gray-800">Faahfaahin</th><th class="p-3 border-b border-gray-800">Debit Account</th><th class="p-3 border-b border-gray-800">Credit Account</th><th class="p-3 border-b border-gray-800">Amount</th><th class="p-3 border-b border-gray-800">Action</th></tr>
                    </thead>
                    <tbody class="divide-y divide-gray-800 text-sm">
                        {% for tx in transactions %}
                        <tr>
                            <td class="p-3 text-gray-400">{{ tx.id }}</td>
                            <td class="p-3 text-gray-400">{{ tx.date }}</td>
                            <td class="p-3 font-medium text-white">{{ tx.description }}</td>
                            <td class="p-3 text-emerald-400 font-semibold">{{ tx.debit_name }}</td>
                            <td class="p-3 text-red-400 font-semibold">{{ tx.credit_name }}</td>
                            <td class="p-3 font-bold text-white">${{ tx.amount }}</td>
                            <td class="p-3 flex gap-2">
                                <button onclick="toggleForm('form-edit-{{ tx.id }}')" class="bg-amber-600 text-white px-3 py-1 rounded-lg text-xs hover:bg-amber-700 transition">Edit</button>
                                <form action="/delete_transaction/{{ tx.id }}" method="POST" onsubmit="return confirm('Ma hubtaa inaad tirtirto macaamilkan?')">
                                    <button type="submit" class="bg-red-600 text-white px-3 py-1 rounded-lg text-xs hover:bg-red-700 transition">Tirtir</button>
                                </form>
                            </td>
                        </tr>
                        <tr id="form-edit-{{ tx.id }}" class="hidden bg-[#0f172a]">
                            <td colspan="7" class="p-4">
                                <form action="/edit_transaction/{{ tx.id }}" method="POST" class="flex gap-3 items-center">
                                    <input type="text" name="description" value="{{ tx.description }}" class="border border-gray-700 p-2 rounded-xl w-1/2 bg-[#1e293b] text-sm text-white" required>
                                    <input type="number" step="any" name="amount" value="{{ tx.amount }}" class="border border-gray-700 p-2 rounded-xl w-1/3 bg-[#1e293b] text-sm text-white" required>
                                    <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded-xl text-xs font-semibold hover:bg-blue-700">Keydi</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>

        </div>
    </div>

    <!-- JavaScript-ka PWA Installation -->
    <script>
        let deferredPrompt;
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            const installBtn = document.getElementById('install-btn');
            if (installBtn) {
                installBtn.style.display = 'flex';
            }
        });

        const installBtn = document.getElementById('install-btn');
        if (installBtn) {
            installBtn.addEventListener('click', async () => {
                if (deferredPrompt) {
                    deferredPrompt.prompt();
                    const { outcome } = await deferredPrompt.userChoice;
                    if (outcome === 'accepted') {
                        console.log('App-kii waa la rakibay');
                    }
                    deferredPrompt = null;
                    installBtn.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    conn = get_db_connection()
    inventory = conn.execute("SELECT * FROM inventory").fetchall()
    accounts = conn.execute("SELECT * FROM account").fetchall()

    transactions_raw = conn.execute("""
        SELECT t.*, 
               da.name as debit_name, 
               ca.name as credit_name 
        FROM wadar_trans t
        JOIN account da ON t.debit_account_id = da.id
        JOIN account ca ON t.credit_account_id = ca.id
    """).fetchall()

    cash_row = conn.execute(
        "SELECT balance FROM account WHERE name = 'Cash on Hand'"
    ).fetchone()
    rev_row = conn.execute(
        "SELECT SUM(balance) as total FROM account WHERE type = 'Revenue'"
    ).fetchone()
    exp_row = conn.execute(
        "SELECT SUM(balance) as total FROM account WHERE type = 'Expense'"
    ).fetchone()
    conn.close()

    cash_balance = cash_row["balance"] if cash_row else 0.0
    total_rev = rev_row["total"] if rev_row and rev_row["total"] else 0.0
    total_exp = exp_row["total"] if exp_row and exp_row["total"] else 0.0
    net_profit = total_rev - total_exp

    return render_template_string(
        HTML_TEMPLATE,
        inventory=inventory,
        transactions=transactions_raw,
        accounts=accounts,
        cash_balance=cash_balance,
        total_revenue=total_rev,
        total_expenses=total_exp,
        net_profit=net_profit,
    )


def post_transaction(description, debit_name, credit_name, amount, tx_date):
    conn = get_db_connection()
    cursor = conn.cursor()

    debit_acc = cursor.execute(
        "SELECT * FROM account WHERE name = ?", (debit_name,)
    ).fetchone()
    credit_acc = cursor.execute(
        "SELECT * FROM account WHERE name = ?", (credit_name,)
    ).fetchone()

    if debit_acc and credit_acc:
        d_new_bal = (
            debit_acc["balance"] + amount
            if debit_acc["type"] in ["Asset", "Expense"]
            else debit_acc["balance"] - amount
        )
        cursor.execute(
            "UPDATE account SET balance = ? WHERE id = ?",
            (d_new_bal, debit_acc["id"]),
        )

        c_new_bal = (
            credit_acc["balance"] + amount
            if credit_acc["type"] in ["Revenue", "Liability", "Equity"]
            else credit_acc["balance"] - amount
        )
        cursor.execute(
            "UPDATE account SET balance = ? WHERE id = ?",
            (c_new_bal, credit_acc["id"]),
        )

        cursor.execute(
            """
            INSERT INTO wadar_trans (date, description, debit_account_id, credit_account_id, amount)
            VALUES (?, ?, ?, ?, ?)
        """,
            (tx_date, description, debit_acc["id"], credit_acc["id"], amount),
        )
        conn.commit()
    conn.close()


@app.route("/edit_transaction/<int:id>", methods=["POST"])
def edit_transaction(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    tx = cursor.execute("SELECT * FROM wadar_trans WHERE id = ?", (id,)).fetchone()
    if tx:
        debit_acc = cursor.execute(
            "SELECT * FROM account WHERE id = ?", (tx["debit_account_id"],)
        ).fetchone()
        if debit_acc:
            old_d_bal = (
                debit_acc["balance"] - tx["amount"]
                if debit_acc["type"] in ["Asset", "Expense"]
                else debit_acc["balance"] + tx["amount"]
            )
            cursor.execute(
                "UPDATE account SET balance = ? WHERE id = ?",
                (old_d_bal, debit_acc["id"]),
            )

        credit_acc = cursor.execute(
            "SELECT * FROM account WHERE id = ?", (tx["credit_account_id"],)
        ).fetchone()
        if credit_acc:
            old_c_bal = (
                credit_acc["balance"] - tx["amount"]
                if credit_acc["type"] in ["Revenue", "Liability", "Equity"]
                else credit_acc["balance"] + tx["amount"]
            )
            cursor.execute(
                "UPDATE account SET balance = ? WHERE id = ?",
                (old_c_bal, credit_acc["id"]),
            )

        new_amount = float(request.form.get("amount"))
        new_desc = request.form.get("description")

        updated_debit = cursor.execute(
            "SELECT * FROM account WHERE id = ?", (tx["debit_account_id"],)
        ).fetchone()
        if updated_debit:
            new_d_bal = (
                updated_debit["balance"] + new_amount
                if updated_debit["type"] in ["Asset", "Expense"]
                else updated_debit["balance"] - new_amount
            )
            cursor.execute(
                "UPDATE account SET balance = ? WHERE id = ?",
                (new_d_bal, updated_debit["id"]),
            )

        updated_credit = cursor.execute(
            "SELECT * FROM account WHERE id = ?", (tx["credit_account_id"],)
        ).fetchone()
        if updated_credit:
            new_c_bal = (
                updated_credit["balance"] + new_amount
                if updated_credit["type"] in ["Revenue", "Liability", "Equity"]
                else updated_credit["balance"] - new_amount
            )
            cursor.execute(
                "UPDATE account SET balance = ? WHERE id = ?",
                (new_c_bal, updated_credit["id"]),
            )

        cursor.execute(
            """
            UPDATE wadar_trans SET amount = ?, description = ? WHERE id = ?
        """,
            (new_amount, new_desc, id),
        )

        conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/delete_transaction/<int:id>", methods=["POST"])
def delete_transaction(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    tx = cursor.execute(
        "SELECT * FROM wadar_trans WHERE id = ?", (id,)
    ).fetchone()

    if tx:
        debit_acc = cursor.execute(
            "SELECT * FROM account WHERE id = ?", (tx["debit_account_id"],)
        ).fetchone()
        credit_acc = cursor.execute(
            "SELECT * FROM account WHERE id = ?", (tx["credit_account_id"],)
        ).fetchone()

        if debit_acc:
            d_new_bal = (
                debit_acc["balance"] - tx["amount"]
                if debit_acc["type"] in ["Asset", "Expense"]
                else debit_acc["balance"] + tx["amount"]
            )
            cursor.execute(
                "UPDATE account SET balance = ? WHERE id = ?",
                (d_new_bal, debit_acc["id"]),
            )

        if credit_acc:
            c_new_bal = (
                credit_acc["balance"] - tx["amount"]
                if credit_acc["type"] in ["Revenue", "Liability", "Equity"]
                else credit_acc["balance"] + tx["amount"]
            )
            cursor.execute(
                "UPDATE account SET balance = ? WHERE id = ?",
                (c_new_bal, credit_acc["id"]),
            )

        cursor.execute("DELETE FROM wadar_trans WHERE id = ?", (id,))
        conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/export_inventory_excel")
def export_inventory_excel():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventory")
    output.seek(0)

    return send_file(
        output,
        download_name="Inventory_Report.xlsx",
        as_attachment=True,
        mimetype=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )


@app.route("/import_inventory", methods=["POST"])
def import_inventory():
    if "file" not in request.files:
        return redirect(url_for("index"))

    file = request.files["file"]
    if file.filename == "":
        return redirect(url_for("index"))

    if file:
        df = pd.read_excel(file)
        conn = get_db_connection()
        cursor = conn.cursor()
        for _, row in df.iterrows():
            cursor.execute(
                """
                INSERT INTO inventory (item, qty, cost_price, selling_price)
                VALUES (?, ?, ?, ?)
            """,
                (
                    str(row["Item Name"]),
                    float(row["Tirada"]),
                    float(row["Cost Price"]),
                    float(row["Selling Price"]),
                ),
            )
        conn.commit()
        conn.close()
    return redirect(url_for("index"))


@app.route("/add_inventory", methods=["POST"])
def add_inventory():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO inventory (item, qty, cost_price, selling_price)
        VALUES (?, ?, ?, ?)
    """,
        (
            request.form.get("item"),
            float(request.form.get("qty")),
            float(request.form.get("cost_price")),
            float(request.form.get("selling_price")),
        ),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/delete_inventory/<int:id>", methods=["POST"])
def delete_inventory(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/update_inventory/<int:id>", methods=["POST"])
def update_inventory(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE inventory SET item = ?, qty = ?, cost_price = ?, selling_price = ?
        WHERE id = ?
    """,
        (
            request.form.get("item"),
            float(request.form.get("qty")),
            float(request.form.get("cost_price")),
            float(request.form.get("selling_price")),
            id,
        ),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/add_sale", methods=["POST"])
def add_sale():
    inventory_id = request.form.get("inventory_id")
    sold_qty = float(request.form.get("quantity"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ka soo aqri alaabta kaydka ku jirta
    item_row = cursor.execute(
        "SELECT * FROM inventory WHERE id = ?", (inventory_id,)
    ).fetchone()

    if item_row:
        current_qty = item_row["qty"]
        if current_qty >= sold_qty:
            # 1. Ka jar tirada alaabta kaydka si automatic ah
            new_qty = current_qty - sold_qty
            cursor.execute(
                "UPDATE inventory SET qty = ? WHERE id = ?",
                (new_qty, inventory_id),
            )
            conn.commit()
        else:
            conn.close()
            return "Waan ka xunnahay, tirada alaabta ee kaydka ku jirta waa ka yar tahay inta aad iibinayso!"

    conn.close()

    # 2. Diiwaangeli xisaabta dakhliga (Double-Entry: Cash on Hand vs Sales Revenue)
    post_transaction(
        request.form.get("description"),
        "Cash on Hand",
        "Sales Revenue",
        float(request.form.get("amount")),
        request.form.get("transaction_date"),
    )
    return redirect(url_for("index"))


@app.route("/add_purchase", methods=["POST"])
def add_purchase():
    post_transaction(
        request.form.get("description"),
        "Purchases Expense",
        "Cash on Hand",
        float(request.form.get("amount")),
        request.form.get("transaction_date"),
    )
    return redirect(url_for("index"))


@app.route("/add_income", methods=["POST"])
def add_income():
    post_transaction(
        request.form.get("description"),
        "Cash on Hand",
        "Other Income",
        float(request.form.get("amount")),
        request.form.get("transaction_date"),
    )
    return redirect(url_for("index"))


@app.route("/add_expense", methods=["POST"])
def app_expense():
    post_transaction(
        request.form.get("description"),
        "Operating Expenses",
        "Cash on Hand",
        float(request.form.get("amount")),
        request.form.get("transaction_date"),
    )
    return redirect(url_for("index"))


@app.route("/add_opening_balance", methods=["POST"])
def add_opening_balance():
    post_transaction(
        request.form.get("description"),
        request.form.get("debit_account"),
        "Owner's Capital",
        float(request.form.get("amount")),
        request.form.get("transaction_date"),
    )
    return redirect(url_for("index"))


@app.route("/add_manual_journal", methods=["POST"])
def add_manual_journal():
    post_transaction(
        request.form.get("description"),
        request.form.get("debit_account"),
        request.form.get("credit_account"),
        float(request.form.get("amount")),
        request.form.get("transaction_date"),
    )
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
