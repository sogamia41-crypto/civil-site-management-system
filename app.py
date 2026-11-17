from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
DB = BASE / "site_management.db"

app = Flask(__name__)
app.secret_key = "civil-site-demo-secret"
app.config["TODAY"] = datetime.now().strftime("%Y-%m-%d")


# =========================================================
# Database
# =========================================================

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        trade TEXT NOT NULL,
        contact TEXT,
        phone TEXT,
        tax_id TEXT,
        rating INTEGER DEFAULT 5,
        note TEXT
    );

    CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        unit TEXT NOT NULL,
        min_stock REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS material_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material_id INTEGER NOT NULL,
        vendor_id INTEGER,
        log_type TEXT NOT NULL CHECK(log_type IN ('進貨','領料')),
        quantity REAL NOT NULL,
        unit_price REAL DEFAULT 0,
        invoice_no TEXT,
        reconciled INTEGER DEFAULT 0,
        log_date TEXT NOT NULL,
        note TEXT,
        FOREIGN KEY(material_id)
            REFERENCES materials(id)
            ON DELETE CASCADE,
        FOREIGN KEY(vendor_id)
            REFERENCES vendors(id)
            ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        payee TEXT,
        expense_date TEXT NOT NULL,
        reimbursed INTEGER DEFAULT 0,
        note TEXT
    );

    CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        borrower TEXT NOT NULL,
        checkout_date TEXT NOT NULL,
        return_date TEXT,
        status TEXT NOT NULL DEFAULT '借出',
        note TEXT
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT '行政',
        task_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT '待處理',
        note TEXT
    );
    """)

    conn.commit()
    conn.close()


# =========================================================
# Seed demo data
# =========================================================

def seed():
    conn = get_db()

    # 協力廠商
    if conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0] == 0:
        conn.executemany("""
            INSERT INTO vendors
            (name, trade, contact, phone, tax_id, rating, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            ("永盛模板工程", "模板", "王先生", "0912-345-678", "12345678", 5, "模板工程協力廠商"),
            ("宏達鋼筋工程", "鋼筋", "陳先生", "0922-456-789", "23456789", 5, "鋼筋綁紮"),
            ("順安水電工程", "水電", "林先生", "0933-567-890", "34567890", 4, "水電工程"),
            ("大成土方工程", "土方", "張先生", "0944-678-901", "45678901", 4, "土方及機具"),
        ])

    # 材料
    if conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0] == 0:
        conn.executemany("""
            INSERT INTO materials
            (name, unit, min_stock)
            VALUES (?, ?, ?)
        """, [
            ("水泥", "包", 50),
            ("鋼筋", "噸", 10),
            ("砂石", "m³", 20),
            ("模板", "m²", 100),
        ])

    # 進出貨紀錄
    if conn.execute("SELECT COUNT(*) FROM material_logs").fetchone()[0] == 0:
        material_ids = {
            row["name"]: row["id"]
            for row in conn.execute("SELECT id, name FROM materials").fetchall()
        }

        vendor_ids = {
            row["name"]: row["id"]
            for row in conn.execute("SELECT id, name FROM vendors").fetchall()
        }

        today = datetime.now().strftime("%Y-%m-%d")

        conn.executemany("""
            INSERT INTO material_logs
            (material_id, vendor_id, log_type, quantity,
             unit_price, invoice_no, reconciled, log_date, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                material_ids["水泥"],
                vendor_ids["大成土方工程"],
                "進貨",
                50,
                180,
                "INV001",
                1,
                today,
                "水泥進場"
            ),
            (
                material_ids["水泥"],
                None,
                "領料",
                15,
                0,
                None,
                1,
                today,
                "現場使用"
            ),
            (
                material_ids["鋼筋"],
                vendor_ids["宏達鋼筋工程"],
                "進貨",
                12,
                28000,
                "INV002",
                1,
                today,
                "鋼筋進場"
            ),
            (
                material_ids["砂石"],
                vendor_ids["大成土方工程"],
                "進貨",
                30,
                900,
                "INV003",
                1,
                today,
                "砂石進場"
            ),
            (
                material_ids["模板"],
                vendor_ids["永盛模板工程"],
                "進貨",
                150,
                850,
                "INV004",
                1,
                today,
                "模板材料進場"
            ),
            (
                material_ids["模板"],
                None,
                "領料",
                20,
                0,
                None,
                1,
                today,
                "模板使用"
            ),
        ])

    # 零用金
    if conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 0:
        today = datetime.now().strftime("%Y-%m-%d")

        conn.executemany("""
            INSERT INTO expenses
            (category, description, amount, payee,
             expense_date, reimbursed, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            ("交通", "工地交通費", 300, "張三", today, 0, "工地巡查"),
            ("文具", "工程文件用品", 450, "張三", today, 1, "行政用品"),
            ("雜支", "現場雜項支出", 800, "張三", today, 0, "工地使用"),
        ])

    # 機具
    if conn.execute("SELECT COUNT(*) FROM equipment").fetchone()[0] == 0:
        today = datetime.now().strftime("%Y-%m-%d")

        conn.executemany("""
            INSERT INTO equipment
            (name, borrower, checkout_date, return_date, status, note)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            ("雷射水平儀", "王工程師", today, None, "借出", "現場放樣"),
            ("電鑽", "陳先生", today, None, "借出", "模板施工"),
        ])

    # 待辦事項
    if conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
        today = datetime.now().strftime("%Y-%m-%d")

        conn.executemany("""
            INSERT INTO tasks
            (title, category, task_date, status, note)
            VALUES (?, ?, ?, ?, ?)
        """, [
            (
                "訂購模板材料",
                "材料",
                today,
                "待處理",
                "確認模板數量及進場日期"
            ),
            (
                "通知水電廠商進場",
                "協力廠商",
                today,
                "進行中",
                "確認水電施工人員及進場時間"
            ),
            (
                "整理本週出工簽到表",
                "行政",
                today,
                "待處理",
                "完成本週出工紀錄整理"
            ),
        ])

    conn.commit()
    conn.close()


# =========================================================
# Dashboard
# =========================================================

@app.route("/")
def dashboard():
    conn = get_db()

    stats = {
        "vendors": conn.execute(
            "SELECT COUNT(*) FROM vendors"
        ).fetchone()[0],

        "materials": conn.execute(
            "SELECT COUNT(*) FROM materials"
        ).fetchone()[0],

        "logs": conn.execute(
            "SELECT COUNT(*) FROM material_logs"
        ).fetchone()[0],

        "expenses": conn.execute(
            "SELECT COUNT(*) FROM expenses"
        ).fetchone()[0],

        "equipment": conn.execute(
            "SELECT COUNT(*) FROM equipment WHERE status = '借出'"
        ).fetchone()[0],

        "tasks": conn.execute("""
            SELECT COUNT(*)
            FROM tasks
            WHERE status != '已完成'
        """).fetchone()[0],
    }

    materials = conn.execute("""
        SELECT
            m.id,
            m.name,
            m.unit,
            m.min_stock,
            COALESCE(
                SUM(
                    CASE
                        WHEN ml.log_type = '進貨'
                        THEN ml.quantity
                        WHEN ml.log_type = '領料'
                        THEN -ml.quantity
                        ELSE 0
                    END
                ),
                0
            ) AS stock
        FROM materials m
        LEFT JOIN material_logs ml
            ON m.id = ml.material_id
        GROUP BY
            m.id,
            m.name,
            m.unit,
            m.min_stock
        ORDER BY m.id
    """).fetchall()

    tasks = conn.execute("""
        SELECT *
        FROM tasks
        ORDER BY
            CASE
                WHEN status = '待處理' THEN 1
                WHEN status = '進行中' THEN 2
                ELSE 3
            END,
            task_date DESC,
            id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        stats=stats,
        materials=materials,
        tasks=tasks
    )


# =========================================================
# Tasks
# =========================================================

@app.route("/tasks", methods=["GET", "POST"])
def tasks():
    conn = get_db()

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        category = request.form.get("category", "行政")
        task_date = request.form.get(
            "task_date",
            app.config["TODAY"]
        )
        note = request.form.get("note", "").strip()

        if not title:
            flash("請輸入待辦事項")
            conn.close()
            return redirect(url_for("tasks"))

        conn.execute("""
            INSERT INTO tasks
            (title, category, task_date, status, note)
            VALUES (?, ?, ?, '待處理', ?)
        """, (
            title,
            category,
            task_date,
            note
        ))

        conn.commit()
        conn.close()

        flash("待辦事項新增成功")
        return redirect(url_for("tasks"))

    task_list = conn.execute("""
        SELECT *
        FROM tasks
        ORDER BY task_date DESC, id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "tasks.html",
        tasks=task_list
    )


@app.route("/tasks/update/<int:id>", methods=["POST"])
def task_update(id):

    status = request.form.get(
        "status",
        "待處理"
    )

    allowed_status = {
        "待處理",
        "進行中",
        "已完成"
    }

    if status not in allowed_status:
        status = "待處理"

    conn = get_db()

    conn.execute("""
        UPDATE tasks
        SET status = ?
        WHERE id = ?
    """, (
        status,
        id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("tasks"))


@app.route("/tasks/delete/<int:id>", methods=["POST"])
def task_delete(id):

    conn = get_db()

    conn.execute("""
        DELETE FROM tasks
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    flash("待辦事項已刪除")

    return redirect(url_for("tasks"))


# =========================================================
# Vendors
# =========================================================

@app.route("/vendors")
def vendors():
    conn = get_db()

    vendors = conn.execute("""
        SELECT *
        FROM vendors
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "vendors.html",
        vendors=vendors
    )


@app.route("/vendors/add", methods=["GET", "POST"])
def vendor_add():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        trade = request.form.get("trade", "").strip()
        contact = request.form.get("contact", "").strip()
        phone = request.form.get("phone", "").strip()
        tax_id = request.form.get("tax_id", "").strip()
        rating = request.form.get("rating", 5)
        note = request.form.get("note", "").strip()

        if not name or not trade:
            flash("請填寫廠商名稱及工種")
            return redirect(url_for("vendor_add"))

        conn = get_db()

        conn.execute("""
            INSERT INTO vendors
            (name, trade, contact, phone, tax_id, rating, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            trade,
            contact,
            phone,
            tax_id,
            rating,
            note
        ))

        conn.commit()
        conn.close()

        flash("協力廠商新增成功")

        return redirect(url_for("vendors"))

    return render_template("vendor_form.html")


@app.route("/vendors/edit/<int:id>", methods=["GET", "POST"])
def vendor_edit(id):

    conn = get_db()

    vendor = conn.execute("""
        SELECT *
        FROM vendors
        WHERE id = ?
    """, (id,)).fetchone()

    if not vendor:
        conn.close()
        return "找不到協力廠商", 404

    if request.method == "POST":

        conn.execute("""
            UPDATE vendors
            SET name = ?,
                trade = ?,
                contact = ?,
                phone = ?,
                tax_id = ?,
                rating = ?,
                note = ?
            WHERE id = ?
        """, (
            request.form.get("name", "").strip(),
            request.form.get("trade", "").strip(),
            request.form.get("contact", "").strip(),
            request.form.get("phone", "").strip(),
            request.form.get("tax_id", "").strip(),
            request.form.get("rating", 5),
            request.form.get("note", "").strip(),
            id
        ))

        conn.commit()
        conn.close()

        flash("協力廠商資料已更新")

        return redirect(url_for("vendors"))

    conn.close()

    return render_template(
        "vendor_form.html",
        vendor=vendor
    )


@app.route("/vendors/delete/<int:id>", methods=["POST"])
def vendor_delete(id):

    conn = get_db()

    conn.execute("""
        DELETE FROM vendors
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    flash("協力廠商已刪除")

    return redirect(url_for("vendors"))


# =========================================================
# Materials
# =========================================================

@app.route("/materials")
def materials():

    conn = get_db()

    materials = conn.execute("""
        SELECT
            m.*,
            COALESCE(
                SUM(
                    CASE
                        WHEN ml.log_type = '進貨'
                            THEN ml.quantity
                        WHEN ml.log_type = '領料'
                            THEN -ml.quantity
                        ELSE 0
                    END
                ),
                0
            ) AS stock
        FROM materials m
        LEFT JOIN material_logs ml
            ON m.id = ml.material_id
        GROUP BY
            m.id,
            m.name,
            m.unit,
            m.min_stock
        ORDER BY m.id
    """).fetchall()

    conn.close()

    return render_template(
        "materials.html",
        materials=materials
    )


@app.route("/materials/add", methods=["GET", "POST"])
def material_add():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        unit = request.form.get("unit", "").strip()
        min_stock = request.form.get(
            "min_stock",
            0
        )

        if not name or not unit:
            flash("請填寫材料名稱及單位")
            return redirect(url_for("material_add"))

        conn = get_db()

        try:
            conn.execute("""
                INSERT INTO materials
                (name, unit, min_stock)
                VALUES (?, ?, ?)
            """, (
                name,
                unit,
                min_stock
            ))

            conn.commit()

        except sqlite3.IntegrityError:

            flash("材料名稱已存在")

            conn.close()

            return redirect(url_for("material_add"))

        conn.close()

        flash("材料新增成功")

        return redirect(url_for("materials"))

    return render_template("material_form.html")


@app.route("/materials/edit/<int:id>", methods=["GET", "POST"])
def material_edit(id):

    conn = get_db()

    material = conn.execute("""
        SELECT *
        FROM materials
        WHERE id = ?
    """, (id,)).fetchone()

    if not material:
        conn.close()
        return "找不到材料", 404

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        unit = request.form.get("unit", "").strip()
        min_stock = request.form.get(
            "min_stock",
            0
        )

        conn.execute("""
            UPDATE materials
            SET name = ?,
                unit = ?,
                min_stock = ?
            WHERE id = ?
        """, (
            name,
            unit,
            min_stock,
            id
        ))

        conn.commit()
        conn.close()

        flash("材料資料已更新")

        return redirect(url_for("materials"))

    conn.close()

    return render_template(
        "material_form.html",
        material=material
    )


@app.route("/materials/delete/<int:id>", methods=["POST"])
def material_delete(id):

    conn = get_db()

    conn.execute("""
        DELETE FROM materials
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    flash("材料已刪除")

    return redirect(url_for("materials"))


# =========================================================
# Material logs
# =========================================================

@app.route("/material-logs")
def material_logs():

    conn = get_db()

    logs = conn.execute("""
        SELECT
            ml.*,
            m.name AS material_name,
            m.unit AS material_unit,
            v.name AS vendor_name
        FROM material_logs ml
        JOIN materials m
            ON ml.material_id = m.id
        LEFT JOIN vendors v
            ON ml.vendor_id = v.id
        ORDER BY ml.log_date DESC, ml.id DESC
    """).fetchall()

    materials = conn.execute("""
        SELECT *
        FROM materials
        ORDER BY name
    """).fetchall()

    vendors = conn.execute("""
        SELECT *
        FROM vendors
        ORDER BY name
    """).fetchall()

    conn.close()

    return render_template(
        "material_logs.html",
        logs=logs,
        materials=materials,
        vendors=vendors
    )


@app.route("/material-logs/add", methods=["POST"])
def material_log_add():

    material_id = request.form.get("material_id")
    vendor_id = request.form.get("vendor_id") or None
    log_type = request.form.get("log_type")
    quantity = request.form.get("quantity", 0)
    unit_price = request.form.get("unit_price", 0)
    invoice_no = request.form.get("invoice_no", "").strip()
    log_date = request.form.get(
        "log_date",
        app.config["TODAY"]
    )
    note = request.form.get("note", "").strip()

    if not material_id or not log_type:
        flash("請填寫必要資料")
        return redirect(url_for("material_logs"))

    conn = get_db()

    conn.execute("""
        INSERT INTO material_logs
        (material_id, vendor_id, log_type, quantity,
         unit_price, invoice_no, reconciled, log_date, note)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
    """, (
        material_id,
        vendor_id,
        log_type,
        quantity,
        unit_price,
        invoice_no,
        log_date,
        note
    ))

    conn.commit()
    conn.close()

    flash("進出貨紀錄新增成功")

    return redirect(url_for("material_logs"))


@app.route("/material-logs/delete/<int:id>", methods=["POST"])
def material_log_delete(id):

    conn = get_db()

    conn.execute("""
        DELETE FROM material_logs
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    flash("進出貨紀錄已刪除")

    return redirect(url_for("material_logs"))


# =========================================================
# Expenses
# =========================================================

@app.route("/expenses")
def expenses():

    conn = get_db()

    expenses = conn.execute("""
        SELECT *
        FROM expenses
        ORDER BY expense_date DESC, id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "expenses.html",
        expenses=expenses
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def expense_add():

    if request.method == "POST":

        category = request.form.get(
            "category",
            "雜支"
        )

        description = request.form.get(
            "description",
            ""
        ).strip()

        amount = request.form.get(
            "amount",
            0
        )

        payee = request.form.get(
            "payee",
            ""
        ).strip()

        expense_date = request.form.get(
            "expense_date",
            app.config["TODAY"]
        )

        reimbursed = 1 if request.form.get(
            "reimbursed"
        ) else 0

        note = request.form.get(
            "note",
            ""
        ).strip()

        if not description:
            flash("請輸入支出說明")
            return redirect(url_for("expense_add"))

        conn = get_db()

        conn.execute("""
            INSERT INTO expenses
            (category, description, amount, payee,
             expense_date, reimbursed, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            category,
            description,
            amount,
            payee,
            expense_date,
            reimbursed,
            note
        ))

        conn.commit()
        conn.close()

        flash("零用金紀錄新增成功")

        return redirect(url_for("expenses"))

    return render_template("expense_form.html")


@app.route("/expenses/delete/<int:id>", methods=["POST"])
def expense_delete(id):

    conn = get_db()

    conn.execute("""
        DELETE FROM expenses
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    flash("零用金紀錄已刪除")

    return redirect(url_for("expenses"))


# =========================================================
# Equipment
# =========================================================

@app.route("/equipment")
def equipment():

    conn = get_db()

    equipment = conn.execute("""
        SELECT *
        FROM equipment
        ORDER BY
            CASE
                WHEN status = '借出' THEN 1
                ELSE 2
            END,
            id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "equipment.html",
        equipment=equipment
    )


@app.route("/equipment/add", methods=["GET", "POST"])
def equipment_add():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        borrower = request.form.get(
            "borrower",
            ""
        ).strip()

        checkout_date = request.form.get(
            "checkout_date",
            app.config["TODAY"]
        )

        note = request.form.get(
            "note",
            ""
        ).strip()

        if not name or not borrower:
            flash("請填寫機具名稱及借用人")
            return redirect(url_for("equipment_add"))

        conn = get_db()

        conn.execute("""
            INSERT INTO equipment
            (name, borrower, checkout_date,
             status, note)
            VALUES (?, ?, ?, '借出', ?)
        """, (
            name,
            borrower,
            checkout_date,
            note
        ))

        conn.commit()
        conn.close()

        flash("機具借出紀錄新增成功")

        return redirect(url_for("equipment"))

    return render_template("equipment_form.html")


@app.route("/equipment/return/<int:id>", methods=["POST"])
def equipment_return(id):

    conn = get_db()

    conn.execute("""
        UPDATE equipment
        SET status = '已歸還',
            return_date = ?
        WHERE id = ?
    """, (
        app.config["TODAY"],
        id
    ))

    conn.commit()
    conn.close()

    flash("機具已登記歸還")

    return redirect(url_for("equipment"))


@app.route("/equipment/delete/<int:id>", methods=["POST"])
def equipment_delete(id):

    conn = get_db()

    conn.execute("""
        DELETE FROM equipment
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    flash("機具紀錄已刪除")

    return redirect(url_for("equipment"))


# =========================================================
# API
# =========================================================

@app.route("/api/materials")
def api_materials():

    conn = get_db()

    materials = conn.execute("""
        SELECT
            m.id,
            m.name,
            m.unit,
            m.min_stock,
            COALESCE(
                SUM(
                    CASE
                        WHEN ml.log_type = '進貨'
                            THEN ml.quantity
                        WHEN ml.log_type = '領料'
                            THEN -ml.quantity
                        ELSE 0
                    END
                ),
                0
            ) AS stock
        FROM materials m
        LEFT JOIN material_logs ml
            ON m.id = ml.material_id
        GROUP BY
            m.id,
            m.name,
            m.unit,
            m.min_stock
        ORDER BY m.id
    """).fetchall()

    result = []

    for row in materials:
        result.append({
            "id": row["id"],
            "name": row["name"],
            "unit": row["unit"],
            "stock": row["stock"],
            "min_stock": row["min_stock"],
            "status": (
                "庫存不足"
                if row["stock"] < row["min_stock"]
                else "正常"
            )
        })

    conn.close()

    return jsonify(result)


# =========================================================
# Application startup
# =========================================================

init_db()
seed()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
