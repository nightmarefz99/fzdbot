import logging
from contextlib import asynccontextmanager

import aiomysql

from fzdbot.settings import get_settings

logger = logging.getLogger(__name__)

_connection_pool = None


async def _safe_rollback(conn, source: str = "unknown") -> None:
    """Rollback only when possible; never mask the original exception."""
    if not conn or getattr(conn, "closed", True):
        return
    try:
        await conn.rollback()
    except aiomysql.Error as rollback_error:
        logger.warning("[DB] Rollback skipped (%s): %s", source, rollback_error)


async def init_db_pool():
    global _connection_pool
    settings = get_settings()
    pool_size = 16
    if _connection_pool is None:
        _connection_pool = await aiomysql.create_pool(minsize=1, maxsize=pool_size, **settings.db_config)
        logger.info("Database pool created")
    return _connection_pool


async def get_connection_from_pool():
    """
    Context manager that safely checks out a connection from the pool,
    and returns it afterward (even if errors happen).
    Automatically rebuilds the pool if it breaks.
    """
    global _connection_pool
    conn = None
    if _connection_pool is None:
        raise RuntimeError("Database pool is not initialized")

    try:
        conn = await _connection_pool.acquire()
        await conn.ping(reconnect=True)
        logger.debug("[DB] Got connection from pool: id=%s", id(conn))
    except Exception as error:
        logger.warning("[DB CONNECTION] Failed to get healthy pooled connection: %s", error)
        if conn:
            conn.close()
            _connection_pool.release(conn)
        raise
    return conn


@asynccontextmanager
async def get_db_connection():
    """
    Context manager for safely acquiring and releasing a DB connection.
    Rolls back on error when possible and always releases the connection.
    """
    conn = None
    try:
        conn = await get_connection_from_pool()
        yield conn
    except aiomysql.Error as error:
        await _safe_rollback(conn, source="get_db_connection")
        logger.error("[DB ERROR] %s", error)
        raise
    finally:
        if conn:
            _connection_pool.release(conn)


async def execute_query(conn, query, params=None, fetch="all", is_proc: bool = False):
    """
    Safely executes an SQL query with rollback on error.
    :conn: DB connection object
    :query: SQL query string
    :params: Optional tuple/list of parameters
    :fetch: "all", "one", or None (for INSERT/UPDATE/DELETE)
    :return: Query result or None if no result
    """
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        try:
            if is_proc:
                await cursor.callproc(query, params or ())
            else:
                await cursor.execute(query, params or ())

            if fetch == "all":
                result = await cursor.fetchall()
            elif fetch == "one":
                result = await cursor.fetchone()
            else:
                result = None

            await conn.commit()
            return result
        except Exception as error:
            await _safe_rollback(conn, source="execute_query")
            logger.error("[DB QUERY ERROR]: %s\nQuery: %s\nParams: %s", error, query, params)
            raise
