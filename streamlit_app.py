import os
from pathlib import Path

import mysql.connector
import pandas as pd
import streamlit as st
from mysql.connector.pooling import MySQLConnectionPool


def read_password() -> str:
    password_file = Path(os.environ["DB_PASSWORD_FILE"])
    return password_file.read_text(encoding="utf-8").strip()


@st.cache_resource
def get_connection_pool() -> MySQLConnectionPool:
    return MySQLConnectionPool(
        pool_name="streamlit_pool",
        pool_size=5,
        host=os.environ.get("DB_HOST", "dashboard-mysql"),
        port=int(os.environ.get("DB_PORT", "3306")),
        database=os.environ.get("DB_NAME", "vdi_edu_data"),
        user=os.environ.get("DB_USER", "dashboard_app"),
        password=read_password(),
        charset="utf8mb4",
        connection_timeout=10,
    )


def query_dataframe(sql: str, parameters=None) -> pd.DataFrame:
    connection = get_connection_pool().get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(sql, parameters or ())
        rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=cursor.column_names)
    finally:
        cursor.close()
        connection.close()


st.set_page_config(page_title="VDI Data Dashboard", layout="wide")
st.title("VDI Education Data")

try:
    tables = query_dataframe(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """,
        (os.environ.get("DB_NAME", "vdi_edu_data"),),
    )

    if tables.empty:
        st.warning("The database contains no tables.")
    else:
        table_names = tables["TABLE_NAME"].tolist()
        selected_table = st.selectbox("Select a table", table_names)

        # The name comes from information_schema and is restricted to that list.
        escaped_table = selected_table.replace("`", "``")

        preview = query_dataframe(
            f"SELECT * FROM `{escaped_table}` LIMIT 100"
        )

        st.subheader(f"First 100 rows from {selected_table}")
        st.dataframe(preview, use_container_width=True)

except mysql.connector.Error as error:
    st.error(f"Database connection failed: {error}")