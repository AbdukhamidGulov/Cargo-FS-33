#!/bin/bash
set -e
python /app/migrate_data.py
echo "Данные из text_info.py успешно перенесены в базу данных."