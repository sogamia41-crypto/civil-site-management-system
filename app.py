from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
DB = BASE / "site_management.db"
app = Flask(__name__)
app.secret_key = "civil-site-demo-secret"
app.config['TODAY'] = datetime.now().strftime('%Y-%m-%d')

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
        FOREIGN KEY(material_id) REFERENCES materials(id) ON DELETE CASCADE,
        FOREIGN KEY(vendor_id) REFERENCES vendors(id) ON DELETE SET NULL
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
    """)
    conn.commit()
    conn.close()

def seed():
    conn = get_db()
    if conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO vendors(name,trade,contact,phone,tax_id,rating,note) VALUES(?,?,?,?,?,?,?)",
            [
                ("宏昇混凝土有限公司","混凝土","陳先生","07-1234567","53200123",5,"預拌混凝土"),
                ("建泰鋼鐵有限公司","鋼筋","林小姐","07-2345678","61234567",4,"鋼筋加工配送"),
                ("永固模板工程行","模板","王先生","0912-345-678","81234567",4,"模板施工"),
                ("鼎盛水電工程","水電","張先生","0988-765-432","91234567",5,"水電配管"),
            ])
    if conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO materials(name,unit,min_stock) VALUES(?,?,?)",
            [("水泥","包",50),("鋼筋","噸",10),("砂石","m³",20),("模板","m²",100)]
        )
        materials = {r["name"]: r["id"] for r in conn.execute("SELECT id,name FROM materials")}
        vendors = {r["name"]: r["id"] for r in conn.execute("SELECT id,name FROM vendors")}
        today = datetime.now().strftime("%Y-%m-%d")
        sample = [
            (materials["水泥"],vendors["宏昇混凝土有限公司"],"進貨",80,180,"INV-001",1,today,"初始庫存"),
            (materials["鋼筋"],vendors["建泰鋼鐵有限公司"],"進貨",15,32500,"INV-002",1,today,"SD420"),
            (materials["砂石"],None,"進貨",30,950,"INV-003",0,today,""),
            (materials["模板"],vendors["永固模板工程行"],"進貨",150,420,"INV-004",1,today,""),
            (materials["水泥"],None,"領料",45,0,"",0,today,"A區"),
            (materials["鋼筋"],None,"領料",3,0,"",0,today,"柱筋"),
        ]
        conn.executemany("""INSERT INTO material_logs
            (material_id,vendor_id,log_type,quantity,unit_price,invoice_no,reconciled,log_date,note)
            VALUES(?,?,?,?,?,?,?,?,?)""", sample)
    conn.commit()
    conn.close()

@app.route("/")
def dashboard():
    conn = get_db()
    materials = conn.execute("""
      SELECT m.*, COALESCE(SUM(CASE WHEN l.log_type='進貨' THEN l.quantity
                                   WHEN l.log_type='領料' THEN -l.quantity ELSE 0 END),0) stock
      FROM materials m LEFT JOIN material_logs l ON m.id=l.material_id
      GROUP BY m.id ORDER BY m.id
    """).fetchall()
    stats = {
        "vendors": conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0],
        "materials": len(materials),
        "logs": conn.execute("SELECT COUNT(*) FROM material_logs").fetchone()[0],
        "expenses": conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0],
        "equipment": conn.execute("SELECT COUNT(*) FROM equipment WHERE status='借出'").fetchone()[0]
    }
    conn.close()
    return render_template("dashboard.html", materials=materials, stats=stats)

@app.route("/vendors", methods=["GET","POST"])
def vendors():
    conn = get_db()
    if request.method == "POST":
        conn.execute("""INSERT INTO vendors(name,trade,contact,phone,tax_id,rating,note)
                        VALUES(?,?,?,?,?,?,?)""",
                     (request.form["name"],request.form["trade"],request.form["contact"],
                      request.form["phone"],request.form["tax_id"],request.form.get("rating",5),
                      request.form["note"]))
        conn.commit()
        flash("廠商資料已新增")
        return redirect(url_for("vendors"))
    rows = conn.execute("SELECT * FROM vendors ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("vendors.html", vendors=rows)

@app.route("/vendors/delete/<int:id>", methods=["POST"])
def vendor_delete(id):
    conn=get_db(); conn.execute("DELETE FROM vendors WHERE id=?", (id,)); conn.commit(); conn.close()
    flash("廠商已刪除"); return redirect(url_for("vendors"))

@app.route("/materials", methods=["GET","POST"])
def materials():
    conn=get_db()
    if request.method=="POST":
        try:
            conn.execute("INSERT INTO materials(name,unit,min_stock) VALUES(?,?,?)",
                         (request.form["name"],request.form["unit"],request.form["min_stock"]))
            conn.commit(); flash("材料已新增")
        except sqlite3.IntegrityError:
            flash("材料名稱已存在")
        return redirect(url_for("materials"))
    rows=conn.execute("""
      SELECT m.*, COALESCE(SUM(CASE WHEN l.log_type='進貨' THEN l.quantity
                                   WHEN l.log_type='領料' THEN -l.quantity ELSE 0 END),0) stock
      FROM materials m LEFT JOIN material_logs l ON m.id=l.material_id GROUP BY m.id
    """).fetchall()
    conn.close(); return render_template("materials.html", materials=rows)

@app.route("/logs", methods=["GET","POST"])
def logs():
    conn=get_db()
    if request.method=="POST":
        conn.execute("""INSERT INTO material_logs
          (material_id,vendor_id,log_type,quantity,unit_price,invoice_no,reconciled,log_date,note)
          VALUES(?,?,?,?,?,?,?,?,?)""",
          (request.form["material_id"],request.form.get("vendor_id") or None,request.form["log_type"],
           request.form["quantity"],request.form.get("unit_price",0),request.form["invoice_no"],
           1 if request.form.get("reconciled") else 0,request.form["log_date"],request.form["note"]))
        conn.commit(); flash("材料紀錄已新增"); return redirect(url_for("logs"))
    logs=conn.execute("""SELECT l.*,m.name material,v.name vendor,m.unit
                         FROM material_logs l JOIN materials m ON m.id=l.material_id
                         LEFT JOIN vendors v ON v.id=l.vendor_id ORDER BY l.id DESC""").fetchall()
    materials=conn.execute("SELECT * FROM materials ORDER BY name").fetchall()
    vendors=conn.execute("SELECT * FROM vendors ORDER BY name").fetchall()
    conn.close(); return render_template("logs.html",logs=logs,materials=materials,vendors=vendors)

@app.route("/logs/delete/<int:id>", methods=["POST"])
def log_delete(id):
    conn=get_db(); conn.execute("DELETE FROM material_logs WHERE id=?", (id,)); conn.commit(); conn.close()
    flash("紀錄已刪除"); return redirect(url_for("logs"))

@app.route("/expenses", methods=["GET","POST"])
def expenses():
    conn=get_db()
    if request.method=="POST":
        conn.execute("""INSERT INTO expenses(category,description,amount,payee,expense_date,reimbursed,note)
                        VALUES(?,?,?,?,?,?,?)""",
                     (request.form["category"],request.form["description"],request.form["amount"],
                      request.form["payee"],request.form["expense_date"],
                      1 if request.form.get("reimbursed") else 0,request.form["note"]))
        conn.commit(); flash("零用金紀錄已新增"); return redirect(url_for("expenses"))
    rows=conn.execute("SELECT * FROM expenses ORDER BY expense_date DESC,id DESC").fetchall()
    conn.close(); return render_template("expenses.html",expenses=rows)

@app.route("/equipment", methods=["GET","POST"])
def equipment():
    conn=get_db()
    if request.method=="POST":
        conn.execute("""INSERT INTO equipment(name,borrower,checkout_date,status,note)
                        VALUES(?,?,?,?,?)""",
                     (request.form["name"],request.form["borrower"],request.form["checkout_date"],
                      "借出",request.form["note"]))
        conn.commit(); flash("機具借用已登記"); return redirect(url_for("equipment"))
    rows=conn.execute("SELECT * FROM equipment ORDER BY id DESC").fetchall()
    conn.close(); return render_template("equipment.html",equipment=rows)

@app.route("/equipment/return/<int:id>", methods=["POST"])
def equipment_return(id):
    conn=get_db()
    conn.execute("UPDATE equipment SET status='已歸還',return_date=? WHERE id=?",
                 (datetime.now().strftime("%Y-%m-%d"),id))
    conn.commit(); conn.close(); flash("機具已登記歸還"); return redirect(url_for("equipment"))

@app.route("/api/materials")
def api_materials():
    conn=get_db()
    rows=conn.execute("""SELECT m.name,m.unit,m.min_stock,
      COALESCE(SUM(CASE WHEN l.log_type='進貨' THEN l.quantity
                        WHEN l.log_type='領料' THEN -l.quantity ELSE 0 END),0) stock
      FROM materials m LEFT JOIN material_logs l ON m.id=l.material_id GROUP BY m.id""").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    init_db(); seed()
    app.run(host="0.0.0.0", port=5000, debug=True)
