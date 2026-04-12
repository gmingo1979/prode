# app/utils/prode_puntaje.py

import logging
from app.db import db
from sqlalchemy import text

logger = logging.getLogger(__name__)


def calcular_puntos(partido, pronostico) -> int:
    config = partido.fase.torneo.config
    pts_exacto  = config.resultado_exacto  if config else 3
    pts_parcial = config.resultado_parcial if config else 1
    pts_errado  = config.resultado_errado  if config else 0

    gl_real = partido.goles_local
    gv_real = partido.goles_visitante
    gl_pron = pronostico.goles_local
    gv_pron = pronostico.goles_visitante

    if gl_pron == gl_real and gv_pron == gv_real:
        return pts_exacto

    diff_real = gl_real - gv_real
    diff_pron = gl_pron - gv_pron

    if (diff_real == 0 and diff_pron == 0) or \
       (diff_real > 0 and diff_pron > 0) or \
       (diff_real < 0 and diff_pron < 0):
        return pts_parcial

    return pts_errado


def obtener_ranking_torneo(torneo_id: int) -> list:
    """
    Calcula el ranking de un torneo: posición, puntos, exactos y aciertos
    para cada jugador inscripto y aprobado.

    Returns:
        Lista de dicts ordenada por posición (mejor primero).
    """
    sql = text("""
        SELECT
            u.id                                                        AS usuario_id,
            u.nombre                                                    AS nombre,
            u.apellido                                                  AS apellido,
            COUNT(pr.id)                                                AS pronosticados,
            COALESCE(SUM(pr.puntos), 0)                                 AS puntos,
            COALESCE(SUM(CASE WHEN pr.puntos = cfg.resultado_exacto
                              THEN 1 ELSE 0 END), 0)                    AS exactos,
            COALESCE(SUM(CASE WHEN pr.puntos >= cfg.resultado_parcial
                              THEN 1 ELSE 0 END), 0)                    AS aciertos,
            MAX(pr.updated_at)                                          AS ultimo_pronostico
        FROM prode_inscripciones ins
        JOIN usuarios u                ON u.id  = ins.usuario_id
        JOIN prode_torneos t           ON t.id  = ins.torneo_id
        LEFT JOIN prode_config_puntaje cfg ON cfg.torneo_id = t.id
        LEFT JOIN prode_pronosticos pr     ON pr.usuario_id = u.id
            AND pr.partido_id IN (
                SELECT pa2.id
                FROM prode_partidos pa2
                JOIN prode_fases f2 ON f2.id = pa2.fase_id
                WHERE f2.torneo_id = :torneo_id
                  AND pa2.estado = 'cerrado'
            )
        WHERE ins.torneo_id = :torneo_id
          AND ins.estado    = 'aprobado'
        GROUP BY u.id, u.nombre, u.apellido, cfg.resultado_exacto, cfg.resultado_parcial
    """)

    try:
        rows = db.session.execute(sql, {'torneo_id': torneo_id}).mappings().all()
    except Exception as e:
        logger.error('Ranking SQL error: %s', e)
        return []

    ranking = [dict(row) for row in rows]

    for r in ranking:
        r['usuario'] = f"{r.pop('nombre', '')} {r.pop('apellido', '')}".strip()

    # Resolver avatar_url en una sola query (evita N+1)
    from app.models.usuario import Usuario
    from flask import url_for
    ids = [r['usuario_id'] for r in ranking]
    usuarios_map = {u.id: u for u in Usuario.query.filter(Usuario.id.in_(ids)).all()}
    default_avatar = url_for('static', filename='img/default.svg')
    for r in ranking:
        u = usuarios_map.get(r['usuario_id'])
        r['foto_path'] = u.avatar_url if u else default_avatar

    ranking.sort(key=lambda r: (
        -(r['puntos']   or 0),
        -(r['exactos']  or 0),
        -(r['aciertos'] or 0),
         (str(r['ultimo_pronostico']) if r['ultimo_pronostico'] else '9999'),
         r['usuario_id'],
    ))

    pos_visible = 0
    ultimo_key  = None
    for i, r in enumerate(ranking, 1):
        key = (r['puntos'], r['exactos'], r['aciertos'])
        if key != ultimo_key:
            pos_visible = i
            ultimo_key  = key
        r['posicion'] = pos_visible

    return ranking
