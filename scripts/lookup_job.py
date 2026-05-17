import sqlite3
conn = sqlite3.connect("data/jobs.db")
rows = conn.execute(
    "SELECT title, company, location, job_url FROM seen_jobs WHERE job_url LIKE ?",
    ("%4415403224%",)
).fetchall()
for r in rows:
    print("Título:", r[0])
    print("Empresa:", r[1])
    print("Ubicación:", r[2])
    print("URL:", r[3])
conn.close()
