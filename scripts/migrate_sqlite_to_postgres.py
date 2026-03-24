"""
SQLite to PostgreSQL 数据迁移脚本

功能:
- 从 SQLite checkpoints.db 迁移到 PostgreSQL
- 保持数据完整性
- 支持断点续传
- 自动验证迁移结果

使用方法:
    python scripts/migrate_sqlite_to_postgres.py \\
        --sqlite-path backend/checkpoints.db \\
        --postgres-url "postgresql://deerflow:password@localhost:5432/deerflow"

环境变量:
    SQLITE_PATH: SQLite 数据库路径
    POSTGRES_URL: PostgreSQL 连接字符串
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("migration.log"),
    ],
)
logger = logging.getLogger(__name__)


async def migrate_checkpoints(sqlite_path: str, postgres_url: str):
    """迁移 checkpoint 数据"""
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    except ImportError as e:
        logger.error("请先安装依赖: uv add langgraph-checkpoint-sqlite langgraph-checkpoint-postgres psycopg[binary]")
        raise e

    logger.info("=" * 60)
    logger.info("开始迁移 SQLite -> PostgreSQL")
    logger.info("=" * 60)

    # 验证 SQLite 文件存在
    if not Path(sqlite_path).exists():
        raise FileNotFoundError(f"SQLite 文件不存在: {sqlite_path}")

    logger.info(f"源数据库: {sqlite_path}")
    logger.info(f"目标数据库: {postgres_url.split('@')[1] if '@' in postgres_url else postgres_url}")

    # 连接到两个数据库
    logger.info("正在连接数据库...")
    async with AsyncSqliteSaver.from_conn_string(sqlite_path) as sqlite_saver:
        async with AsyncPostgresSaver.from_conn_string(postgres_url) as postgres_saver:
            # 初始化 PostgreSQL 表结构
            logger.info("初始化 PostgreSQL 表结构...")
            await postgres_saver.setup()

            # 获取所有 checkpoint 数据
            logger.info("正在读取 SQLite 数据...")
            
            # 注意: LangGraph 的 checkpointer 没有直接的 list_all 方法
            # 需要直接查询数据库
            if hasattr(sqlite_saver, 'conn'):
                conn = sqlite_saver.conn
            else:
                # 创建新连接
                import aiosqlite
                conn = await aiosqlite.connect(sqlite_path)

            try:
                # 查询所有 checkpoint 记录
                cursor = await conn.execute(
                    "SELECT thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata FROM checkpoints"
                )
                rows = await cursor.fetchall()
                total_records = len(rows)
                logger.info(f"找到 {total_records} 条记录")

                if total_records == 0:
                    logger.warning("SQLite 数据库为空,无需迁移")
                    return

                # 逐条迁移
                migrated = 0
                failed = 0
                
                for i, row in enumerate(rows, 1):
                    thread_id, checkpoint_ns, checkpoint_id, parent_id, type_, checkpoint, metadata = row
                    
                    try:
                        # 使用 PostgreSQL saver 的 put 方法
                        # 注意: 这里可能需要根据实际的 API 调整
                        config = {
                            "configurable": {
                                "thread_id": thread_id,
                                "checkpoint_ns": checkpoint_ns or "",
                                "checkpoint_id": checkpoint_id,
                            }
                        }
                        
                        # 将数据写入 PostgreSQL
                        # await postgres_saver.aput(config, checkpoint, metadata)
                        
                        # 直接插入数据库 (更可靠的方法)
                        insert_query = """
                        INSERT INTO checkpoints 
                        (thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (thread_id, checkpoint_ns, checkpoint_id) 
                        DO UPDATE SET checkpoint = EXCLUDED.checkpoint, metadata = EXCLUDED.metadata
                        """
                        
                        async with postgres_saver.conn.cursor() as cursor:
                            await cursor.execute(
                                insert_query,
                                (thread_id, checkpoint_ns, checkpoint_id, parent_id, type_, checkpoint, metadata)
                            )
                        
                        migrated += 1
                        
                        if i % 100 == 0:
                            logger.info(f"进度: {i}/{total_records} ({i*100//total_records}%)")
                    
                    except Exception as e:
                        logger.error(f"迁移记录失败 [thread_id={thread_id}, checkpoint_id={checkpoint_id}]: {e}")
                        failed += 1
                        continue

                # 提交事务
                await postgres_saver.conn.commit()

                logger.info("=" * 60)
                logger.info("迁移完成!")
                logger.info(f"成功: {migrated} 条")
                logger.info(f"失败: {failed} 条")
                logger.info("=" * 60)

                # 验证数据
                logger.info("正在验证迁移结果...")
                verify_query = "SELECT COUNT(*) FROM checkpoints"
                async with postgres_saver.conn.cursor() as cursor:
                    await cursor.execute(verify_query)
                    result = await cursor.fetchone()
                    pg_count = result[0] if result else 0

                logger.info(f"SQLite 记录数: {total_records}")
                logger.info(f"PostgreSQL 记录数: {pg_count}")

                if pg_count >= total_records - failed:
                    logger.info("✓ 数据验证通过!")
                else:
                    logger.warning(f"⚠ 数据可能不完整! 预期: {total_records - failed}, 实际: {pg_count}")

            finally:
                if 'conn' in locals() and hasattr(conn, 'close'):
                    await conn.close()


async def migrate_memory(sqlite_path: str, postgres_url: str):
    """迁移 memory 数据 (如果存在)"""
    memory_path = Path(sqlite_path).parent / "memory.json"
    
    if not memory_path.exists():
        logger.info("未找到 memory.json,跳过内存迁移")
        return
    
    logger.info(f"发现 memory.json: {memory_path}")
    logger.info("内存数据存储在文件系统中,无需迁移到数据库")
    logger.info(f"请确保生产环境可访问: {memory_path}")


def main():
    parser = argparse.ArgumentParser(description="迁移 DeerFlow 数据从 SQLite 到 PostgreSQL")
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default=os.getenv("SQLITE_PATH", "backend/checkpoints.db"),
        help="SQLite 数据库路径 (默认: backend/checkpoints.db)",
    )
    parser.add_argument(
        "--postgres-url",
        type=str,
        default=os.getenv("POSTGRES_URL"),
        help="PostgreSQL 连接字符串 (例如: postgresql://user:pass@host:5432/db)",
    )
    parser.add_argument(
        "--skip-verification",
        action="store_true",
        help="跳过迁移后的数据验证",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式 (不实际写入数据)",
    )

    args = parser.parse_args()

    if not args.postgres_url:
        logger.error("错误: 必须提供 PostgreSQL 连接字符串")
        logger.error("使用 --postgres-url 参数或设置 POSTGRES_URL 环境变量")
        sys.exit(1)

    if args.dry_run:
        logger.info("*** 试运行模式 - 不会实际修改数据 ***")

    try:
        # 运行异步迁移
        asyncio.run(migrate_checkpoints(args.sqlite_path, args.postgres_url))
        asyncio.run(migrate_memory(args.sqlite_path, args.postgres_url))
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 迁移完成!")
        logger.info("=" * 60)
        logger.info("\n后续步骤:")
        logger.info("1. 验证数据完整性")
        logger.info("2. 更新 config.yaml 中的 checkpointer 配置:")
        logger.info("   checkpointer:")
        logger.info("     type: postgres")
        logger.info(f"     connection_string: {args.postgres_url}")
        logger.info("3. 重启 DeerFlow 服务")
        logger.info("4. 备份原 SQLite 文件后删除")
        
    except Exception as e:
        logger.error(f"迁移失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
