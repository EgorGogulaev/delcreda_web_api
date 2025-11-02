# После развертывания контейнеров(!):

`crontab -e`

`*/3 * * * * /usr/bin/docker exec -i postgres_delcreda_web /usr/bin/psql -U postgres -d postgres -c "SELECT check_and_toggle_notification_important_status();" >> /var/log/postgres_cron.log 2>&1`

## (!) ВАЖНО:

Периодически нужно чистить лог-файл /var/log/postgres_cron.log

## Сборка:

"""
docker build -t delcreda_web_api .
"""

"""
docker network create --subnet=172.16.237.0/24 delcreda_web_net
"""

## Запуск:

"""
docker run --name postgres_delcreda_web --net delcreda_web_net --ip 172.16.237.10 --restart unless-stopped -e POSTGRES_PASSWORD=\*\*\* -d -p 5432:5432 -v pg_volume_delcreda_web:/var/lib/postgresql/data postgres:15 -c "shared_buffers=800MB" -c "work_mem=8MB" -c "max_connections=80" -c "random_page_cost=1.1" -c "effective_io_concurrency=200" -c "maintenance_work_mem=128MB" -c "effective_cache_size=1400MB" -c "idle_in_transaction_session_timeout=450s" -c "statement_timeout=180s" -c "lock_timeout=300s" -c "log_min_duration_statement=5s"
"""

"""
docker run --name pgbouncer_delcreda_web --net delcreda_web_net --ip 172.16.237.16 --restart unless-stopped -e DATABASE_URL="postgres://postgres:\*\*\*@172.16.237.10:5432/postgres" -e LISTEN_ADDR=0.0.0.0 -e LISTEN_PORT=6432 -e AUTH_TYPE=scram-sha-256 -e POOL_MODE=transaction -e MAX_CLIENT_CONN=300 -e DEFAULT_POOL_SIZE=30 -e RESERVE_POOL_SIZE=10 -e ADMIN_USERS=postgres -p 2346:6432 -d edoburu/pgbouncer
"""

"""
docker run --name redis_delcreda_web --net delcreda_web_net --ip 172.16.237.11 --restart unless-stopped --health-cmd "redis-cli ping" -v redis_volume:/data -p 9736:6379 -d redis:7.2 redis-server --requirepass "\*\*\*"
"""

"""
docker run --name delcreda_web_api --net delcreda_web_net --ip 172.16.237.15 --restart unless-stopped -e IS_PROD=1 -e PORT=8005 -e SECRET_KEY=\*\*\* -e ADMIN_LOGIN=Admin -e ADMIN_PASSWORD=\*\*\* -e ADMIN_TOKEN=\*\*\* -e ADMIN_UUID=\*\*\* -e DB_USER=postgres -e DB_PASS=\*\*\* -e DB_HOST=postgres_delcreda_web -e DB_PORT=5432 -e DB_NAME=postgres -e PG_BOUNCER_HOST=172.16.237.16 -e PG_BOUNCER_PORT=6432 -e SFTP_HOST=172.16.237.14 -e SFTP_PORT=22 -e SFTP_USER=sftpuser -e SFTP_PASS=\*\*\* -e SFTP_BASE_PATH=/upload -e REDIS_PASSWORD=\*\*\* -e REDIS_HOST=redis_delcreda_web -e REDIS_PORT=6379 -e TG_BOT_TOKEN=\*\*\*:\*\*\* -e TG_CHAT_ID=-\*\*\* -p 8005:8005 -d delcreda_web_api
"""
