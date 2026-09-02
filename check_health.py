import os
import app
import sqlite3
import config

routes = list(app.app.url_map.iter_rules())
print(len(routes), 'rotas')

c = sqlite3.connect(config.DB_PATH)
print(c.execute('PRAGMA integrity_check').fetchone()[0])

cur = c.cursor()
cur.execute('SELECT COUNT(*) FROM projects')
print('projects:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM clips')
print('clips:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM transcriptions')
print('transcriptions:', cur.fetchone()[0])

# Font/subtitle health
fonts_dir = os.path.join(os.path.dirname(__file__), 'fonts')
ttf = os.path.join(fonts_dir, 'Montserrat-Bold.ttf')
print('fonts_dir_exists:', os.path.isdir(fonts_dir))
print('montserrat_bold_exists:', os.path.isfile(ttf))
