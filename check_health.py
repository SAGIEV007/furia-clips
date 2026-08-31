import app
import sqlite3
import config

print(len(list(app.app.url_map.iter_rules())), 'rotas')

c = sqlite3.connect(config.DB_PATH)
print(c.execute('PRAGMA integrity_check').fetchone()[0])

# Count projects, clips, transcriptions
cur = c.cursor()
cur.execute('SELECT COUNT(*) FROM projects')
print('projects:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM clips')
print('clips:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM transcriptions')
print('transcriptions:', cur.fetchone()[0])