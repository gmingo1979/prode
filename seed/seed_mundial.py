"""
seed_mundial.py — Carga los datos del Mundial FIFA 2026 en la DB SQLite.

Uso:
    python seed_mundial.py

Usa INSERT OR IGNORE en todo: si algún registro ya existe (mismo id) lo omite.
El torneo id=1 debe existir previamente (creado desde el admin web).
"""

from app import create_app
from app.db import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    conn = db.session.connection()

    # ── Config de puntaje ──────────────────────────────────────────────────
    conn.execute(text("""
        INSERT OR IGNORE INTO prode_config_puntaje
            (id, torneo_id, resultado_exacto, resultado_parcial, resultado_errado)
        VALUES (1, 1, 3, 1, 0)
    """))

    # ── Equipos ────────────────────────────────────────────────────────────
    equipos = [
        (497, 1, 'México',               'A', 'prode/escudos/mx.png',     'mx'),
        (498, 1, 'Sudáfrica',            'A', 'prode/escudos/za.png',     'za'),
        (499, 1, 'Corea del Sur',        'A', 'prode/escudos/kr.png',     'kr'),
        (500, 1, 'República Checa',      'A', 'prode/escudos/cz.png',     'cz'),
        (501, 1, 'Canadá',               'B', 'prode/escudos/ca.png',     'ca'),
        (502, 1, 'Bosnia y Herzegovina', 'B', 'prode/escudos/ba.png',     'ba'),
        (503, 1, 'Qatar',                'B', 'prode/escudos/qa.png',     'qa'),
        (504, 1, 'Suiza',                'B', 'prode/escudos/ch.png',     'ch'),
        (505, 1, 'Escocia',              'C', 'prode/escudos/gb-sct.png', 'gb-sct'),
        (506, 1, 'Marruecos',            'C', 'prode/escudos/ma.png',     'ma'),
        (507, 1, 'Brasil',               'C', 'prode/escudos/br.png',     'br'),
        (508, 1, 'Haití',                'C', 'prode/escudos/ht.png',     'ht'),
        (509, 1, 'Estados Unidos',       'D', 'prode/escudos/us.png',     'us'),
        (510, 1, 'Turquía',              'D', 'prode/escudos/tr.png',     'tr'),
        (511, 1, 'Australia',            'D', 'prode/escudos/au.png',     'au'),
        (512, 1, 'Paraguay',             'D', 'prode/escudos/py.png',     'py'),
        (513, 1, 'Alemania',             'E', 'prode/escudos/de.png',     'de'),
        (514, 1, 'Curazao',              'E', 'prode/escudos/cw.png',     'cw'),
        (515, 1, 'Costa de Marfil',      'E', 'prode/escudos/ci.png',     'ci'),
        (516, 1, 'Ecuador',              'E', 'prode/escudos/ec.png',     'ec'),
        (517, 1, 'Países Bajos',         'F', 'prode/escudos/nl.png',     'nl'),
        (518, 1, 'Suecia',               'F', 'prode/escudos/se.png',     'se'),
        (519, 1, 'Japón',                'F', 'prode/escudos/jp.png',     'jp'),
        (520, 1, 'Túnez',                'F', 'prode/escudos/tn.png',     'tn'),
        (521, 1, 'Irán',                 'G', 'prode/escudos/ir.png',     'ir'),
        (522, 1, 'Nueva Zelanda',        'G', 'prode/escudos/nz.png',     'nz'),
        (523, 1, 'Bélgica',              'G', 'prode/escudos/be.png',     'be'),
        (524, 1, 'Egipto',               'G', 'prode/escudos/eg.png',     'eg'),
        (525, 1, 'España',               'H', 'prode/escudos/es.png',     'es'),
        (526, 1, 'Cabo Verde',           'H', 'prode/escudos/cv.png',     'cv'),
        (527, 1, 'Arabia Saudita',       'H', 'prode/escudos/sa.png',     'sa'),
        (528, 1, 'Uruguay',              'H', 'prode/escudos/uy.png',     'uy'),
        (529, 1, 'Francia',              'I', 'prode/escudos/fr.png',     'fr'),
        (530, 1, 'Iraq',                 'I', 'prode/escudos/iq.png',     'iq'),
        (531, 1, 'Noruega',              'I', 'prode/escudos/no.png',     'no'),
        (532, 1, 'Senegal',              'I', 'prode/escudos/sn.png',     'sn'),
        (533, 1, 'Argentina',            'J', 'prode/escudos/ar.png',     'ar'),
        (534, 1, 'Argelia',              'J', 'prode/escudos/dz.png',     'dz'),
        (535, 1, 'Austria',              'J', 'prode/escudos/at.png',     'at'),
        (536, 1, 'Jordania',             'J', 'prode/escudos/jo.png',     'jo'),
        (537, 1, 'Portugal',             'K', 'prode/escudos/pt.png',     'pt'),
        (538, 1, 'RD Congo',             'K', 'prode/escudos/cd.png',     'cd'),
        (539, 1, 'Uzbekistán',           'K', 'prode/escudos/uz.png',     'uz'),
        (540, 1, 'Colombia',             'K', 'prode/escudos/co.png',     'co'),
        (541, 1, 'Inglaterra',           'L', 'prode/escudos/gb-eng.png', 'gb-eng'),
        (542, 1, 'Croacia',              'L', 'prode/escudos/hr.png',     'hr'),
        (543, 1, 'Ghana',                'L', 'prode/escudos/gh.png',     'gh'),
        (544, 1, 'Panamá',               'L', 'prode/escudos/pa.png',     'pa'),
        # Por definir (fase eliminatoria)
        (545, 1, 'Por definir A',  None, None, None),
        (546, 1, 'Por definir B',  None, None, None),
        (547, 1, 'Por definir C',  None, None, None),
        (548, 1, 'Por definir D',  None, None, None),
        (549, 1, 'Por definir E',  None, None, None),
        (550, 1, 'Por definir F',  None, None, None),
        (551, 1, 'Por definir G',  None, None, None),
        (552, 1, 'Por definir H',  None, None, None),
        (553, 1, 'Por definir I',  None, None, None),
        (554, 1, 'Por definir J',  None, None, None),
        (555, 1, 'Por definir K',  None, None, None),
        (556, 1, 'Por definir L',  None, None, None),
        (557, 1, 'Por definir M',  None, None, None),
        (558, 1, 'Por definir N',  None, None, None),
        (559, 1, 'Por definir O',  None, None, None),
        (560, 1, 'Por definir P',  None, None, None),
    ]
    conn.execute(text("""
        INSERT OR IGNORE INTO prode_equipos
            (id, torneo_id, nombre, grupo, escudo_url, created_at, codigo_iso)
        VALUES (:id, :torneo_id, :nombre, :grupo, :escudo_url, '2026-04-03 04:08:14', :codigo_iso)
    """), [
        dict(id=e[0], torneo_id=e[1], nombre=e[2], grupo=e[3], escudo_url=e[4], codigo_iso=e[5])
        for e in equipos
    ])

    # ── Fases ──────────────────────────────────────────────────────────────
    fases = [
        (55, 1, 'Fase de Grupos',   1),
        (56, 1, 'Ronda de 32',      2),
        (57, 1, 'Octavos de Final', 3),
        (58, 1, 'Cuartos de Final', 4),
        (59, 1, 'Semifinales',      5),
        (60, 1, 'Tercero',          6),
        (61, 1, 'Final',            7),
    ]
    conn.execute(text("""
        INSERT OR IGNORE INTO prode_fases (id, torneo_id, nombre, orden, created_at)
        VALUES (:id, :torneo_id, :nombre, :orden, '2026-04-03 04:08:14')
    """), [dict(id=f[0], torneo_id=f[1], nombre=f[2], orden=f[3]) for f in fases])

    # ── Partidos ───────────────────────────────────────────────────────────
    partidos = [
        # Fase de Grupos (fase_id=55)
        (379, 55, 497, 498, '2026-06-11 16:00:00'),
        (380, 55, 499, 500, '2026-06-11 23:00:00'),
        (381, 55, 501, 502, '2026-06-12 16:00:00'),
        (382, 55, 509, 512, '2026-06-12 22:00:00'),
        (383, 55, 503, 504, '2026-06-13 16:00:00'),
        (384, 55, 507, 506, '2026-06-13 19:00:00'),
        (385, 55, 508, 505, '2026-06-13 22:00:00'),
        (386, 55, 511, 510, '2026-06-14 01:00:00'),
        (387, 55, 513, 514, '2026-06-14 14:00:00'),
        (388, 55, 517, 519, '2026-06-14 17:00:00'),
        (389, 55, 515, 516, '2026-06-14 20:00:00'),
        (390, 55, 518, 520, '2026-06-14 23:00:00'),
        (391, 55, 525, 526, '2026-06-15 13:00:00'),
        (392, 55, 523, 524, '2026-06-15 16:00:00'),
        (393, 55, 527, 528, '2026-06-15 19:00:00'),
        (394, 55, 521, 522, '2026-06-15 22:00:00'),
        (395, 55, 529, 532, '2026-06-16 16:00:00'),
        (396, 55, 530, 531, '2026-06-16 19:00:00'),
        (397, 55, 533, 534, '2026-06-16 22:00:00'),
        (398, 55, 535, 536, '2026-06-17 01:00:00'),
        (399, 55, 537, 538, '2026-06-17 14:00:00'),
        (400, 55, 541, 542, '2026-06-17 17:00:00'),
        (401, 55, 543, 544, '2026-06-17 20:00:00'),
        (402, 55, 539, 540, '2026-06-17 23:00:00'),
        (403, 55, 500, 498, '2026-06-18 13:00:00'),
        (404, 55, 504, 502, '2026-06-18 16:00:00'),
        (405, 55, 501, 503, '2026-06-18 19:00:00'),
        (406, 55, 497, 499, '2026-06-18 22:00:00'),
        (407, 55, 509, 511, '2026-06-19 16:00:00'),
        (408, 55, 505, 506, '2026-06-19 19:00:00'),
        (409, 55, 507, 508, '2026-06-19 21:30:00'),
        (410, 55, 510, 512, '2026-06-20 00:00:00'),
        (411, 55, 517, 518, '2026-06-20 14:00:00'),
        (412, 55, 513, 515, '2026-06-20 17:00:00'),
        (413, 55, 516, 514, '2026-06-20 21:00:00'),
        (414, 55, 520, 519, '2026-06-21 01:00:00'),
        (415, 55, 525, 527, '2026-06-21 13:00:00'),
        (416, 55, 523, 521, '2026-06-21 16:00:00'),
        (417, 55, 528, 526, '2026-06-21 19:00:00'),
        (418, 55, 522, 524, '2026-06-21 22:00:00'),
        (419, 55, 533, 535, '2026-06-22 14:00:00'),
        (420, 55, 529, 530, '2026-06-22 18:00:00'),
        (421, 55, 531, 532, '2026-06-22 21:00:00'),
        (422, 55, 536, 534, '2026-06-23 00:00:00'),
        (423, 55, 537, 539, '2026-06-23 14:00:00'),
        (424, 55, 541, 543, '2026-06-23 17:00:00'),
        (425, 55, 544, 542, '2026-06-23 20:00:00'),
        (426, 55, 540, 538, '2026-06-23 23:00:00'),
        (427, 55, 504, 501, '2026-06-24 16:00:00'),
        (428, 55, 502, 503, '2026-06-24 16:00:00'),
        (429, 55, 506, 508, '2026-06-24 19:00:00'),
        (430, 55, 505, 507, '2026-06-24 19:00:00'),
        (431, 55, 498, 499, '2026-06-24 22:00:00'),
        (432, 55, 500, 497, '2026-06-24 22:00:00'),
        (433, 55, 514, 515, '2026-06-25 17:00:00'),
        (434, 55, 516, 513, '2026-06-25 17:00:00'),
        (435, 55, 520, 517, '2026-06-25 20:00:00'),
        (436, 55, 519, 518, '2026-06-25 20:00:00'),
        (437, 55, 510, 509, '2026-06-25 23:00:00'),
        (438, 55, 512, 511, '2026-06-25 23:00:00'),
        (439, 55, 531, 529, '2026-06-26 16:00:00'),
        (440, 55, 532, 530, '2026-06-26 16:00:00'),
        (441, 55, 526, 527, '2026-06-26 21:00:00'),
        (442, 55, 528, 525, '2026-06-26 21:00:00'),
        (443, 55, 522, 523, '2026-06-27 00:00:00'),
        (444, 55, 524, 521, '2026-06-27 00:00:00'),
        (445, 55, 544, 541, '2026-06-27 18:00:00'),
        (446, 55, 542, 543, '2026-06-27 18:00:00'),
        (447, 55, 540, 537, '2026-06-27 20:30:00'),
        (448, 55, 538, 539, '2026-06-27 20:30:00'),
        (449, 55, 534, 535, '2026-06-27 23:00:00'),
        (450, 55, 536, 533, '2026-06-27 23:00:00'),
        # Ronda de 32 (fase_id=56)
        (451, 56, 545, 546, '2026-06-28 16:00:00'),
        (452, 56, 547, 548, '2026-06-29 17:30:00'),
        (453, 56, 549, 550, '2026-06-29 22:00:00'),
        (454, 56, 551, 552, '2026-06-30 15:00:00'),
        (455, 56, 553, 554, '2026-06-30 21:00:00'),
        (456, 56, 555, 556, '2026-07-01 15:00:00'),
        (457, 56, 557, 558, '2026-07-01 21:00:00'),
        (458, 56, 559, 560, '2026-07-02 15:00:00'),
        (459, 56, 545, 546, '2026-07-02 21:00:00'),
        (460, 56, 547, 548, '2026-07-03 15:00:00'),
        (461, 56, 549, 550, '2026-07-03 21:00:00'),
        (462, 56, 551, 552, '2026-07-04 15:00:00'),
        (463, 56, 553, 554, '2026-07-04 21:00:00'),
        (464, 56, 555, 556, '2026-07-05 15:00:00'),
        (465, 56, 557, 558, '2026-07-05 21:00:00'),
        (466, 56, 559, 560, '2026-07-06 15:00:00'),
        # Octavos de Final (fase_id=57)
        (467, 57, 545, 546, '2026-07-05 15:00:00'),
        (468, 57, 547, 548, '2026-07-05 21:00:00'),
        (469, 57, 549, 550, '2026-07-06 15:00:00'),
        (470, 57, 551, 552, '2026-07-06 21:00:00'),
        (471, 57, 553, 554, '2026-07-07 15:00:00'),
        (472, 57, 555, 556, '2026-07-07 21:00:00'),
        (473, 57, 557, 558, '2026-07-08 15:00:00'),
        (474, 57, 559, 560, '2026-07-08 21:00:00'),
        # Cuartos de Final (fase_id=58)
        (475, 58, 545, 546, '2026-07-10 15:00:00'),
        (476, 58, 547, 548, '2026-07-10 21:00:00'),
        (477, 58, 549, 550, '2026-07-11 15:00:00'),
        (478, 58, 551, 552, '2026-07-11 21:00:00'),
        # Semifinales (fase_id=59)
        (479, 59, 545, 546, '2026-07-14 16:00:00'),
        (480, 59, 547, 548, '2026-07-15 16:00:00'),
        # Tercero (fase_id=60)
        (481, 60, 545, 546, '2026-07-18 18:00:00'),
        # Final (fase_id=61)
        (482, 61, 545, 546, '2026-07-19 16:00:00'),
    ]
    conn.execute(text("""
        INSERT OR IGNORE INTO prode_partidos
            (id, fase_id, equipo_local_id, equipo_visitante_id, fecha_hora,
             goles_local, goles_visitante, estado, created_at)
        VALUES (:id, :fase_id, :loc, :vis, :fh, NULL, NULL, 'pendiente', '2026-04-03 04:08:15')
    """), [
        dict(id=p[0], fase_id=p[1], loc=p[2], vis=p[3], fh=p[4])
        for p in partidos
    ])

    # ── Inscripción del usuario admin (id=1) ───────────────────────────────
    conn.execute(text("""
        INSERT OR IGNORE INTO prode_inscripciones
            (id, usuario_id, torneo_id, estado, created_at)
        VALUES (1, 1, 1, 'aprobado', '2026-04-03 04:09:16')
    """))

    db.session.commit()

    print("✓ Seed completado:")
    print(f"  - {len(equipos)} equipos")
    print(f"  - {len(fases)} fases")
    print(f"  - {len(partidos)} partidos")
    print("  - 1 inscripción")
    print("  - Config de puntaje (3/1/0)")
