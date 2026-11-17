            END,
            task_date ASC,
            id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "tasks.html",
        tasks=rows,
        today=datetime.now().strftime("%Y-%m-%d")
    )


@app.route("/tasks/update/<int:id>", methods=["POST"])
def task_update(id):
    conn = get_db()

    conn.execute("""
        UPDATE tasks
        SET status=?
        WHERE id=?
    """, (
        request.form["status"],
        id
    ))

    conn.commit()
    conn.close()

    flash("待辦事項狀態已更新")

    return redirect(url_for("tasks"))


@app.route("/tasks/delete/<int:id>", methods=["POST"])
def task_delete(id):
    conn = get_db()

    conn.execute(
        "DELETE FROM tasks WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    flash("待辦事項已刪除")

    return redirect(url_for("tasks"))


# =========================
# API：材料庫存
# =========================

@app.route("/api/materials")
def api_materials():
    conn = get_db()

    rows = conn.execute("""
        SELECT
            m.name,
            m.unit,
            m.min_stock,
            COALESCE(
                SUM(
                    CASE
                        WHEN l.log_type='進貨'
                            THEN l.quantity
                        WHEN l.log_type='領料'
                            THEN -l.quantity
                        ELSE 0
                    END
                ), 0
            ) stock
        FROM materials m
        LEFT JOIN material_logs l
            ON m.id=l.material_id
        GROUP BY m.id
    """).fetchall()

    conn.close()

    return jsonify([
        dict(r)
        for r in rows
    ])


# =========================
# 啟動
# =========================

if __name__ == "__main__":
    init_db()
    seed()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
