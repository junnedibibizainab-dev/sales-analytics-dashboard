
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "sample_sales.csv"

REQUIRED_COLUMNS = [
    "order_id",
    "order_date",
    "product",
    "category",
    "region",
    "quantity",
    "unit_price",
    "unit_cost",
    "sales_rep",
]


# --------------------------------------------------
# 2. LOAD AND CLEAN DATA
# --------------------------------------------------

@st.cache_data
def load_sample_data(file_path):
    return pd.read_csv(file_path)


def prepare_data(data):
    """Validate, clean, and calculate sales metrics."""

    data = data.copy()

    # Remove accidental spaces from column names.
    data.columns = data.columns.str.strip()

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    # Convert dates and numeric fields.
    data["order_date"] = pd.to_datetime(
        data["order_date"], errors="coerce"
    )

    numeric_columns = [
        "quantity",
        "unit_price",
        "unit_cost",
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column], errors="coerce"
        )

    # Remove rows with missing required values.
    data = data.dropna(subset=REQUIRED_COLUMNS)

    # Remove duplicate order IDs.
    data = data.drop_duplicates(subset=["order_id"])

    # Ignore impossible or invalid sales records.
    data = data[
        (data["quantity"] > 0)
        & (data["unit_price"] >= 0)
        & (data["unit_cost"] >= 0)
    ].copy()

    if data.empty:
        raise ValueError(
            "No valid sales records were found."
        )

    # Calculate business metrics.
    data["revenue"] = (
        data["quantity"] * data["unit_price"]
    )

    data["profit"] = (
        data["quantity"]
        * (data["unit_price"] - data["unit_cost"])
    )

    return data


# --------------------------------------------------
# 3. APPLICATION HEADER
# --------------------------------------------------

st.title("📊 Sales Analytics Dashboard")

st.write(
    "Analyze revenue, profit, products, and sales "
    "performance using interactive charts."
)

st.caption(
    "Practice project | Currency: Indian Rupees (₹)"
)


# --------------------------------------------------
# 4. UPLOAD OR LOAD SAMPLE DATA
# --------------------------------------------------

st.sidebar.header("Data Source")

uploaded_file = st.sidebar.file_uploader(
    "Upload your sales CSV file",
    type=["csv"],
    help="Your file must contain all nine required columns."
)

try:
    if uploaded_file is not None:
        raw_data = pd.read_csv(uploaded_file)
        source_name = uploaded_file.name
    else:
        if not DATA_FILE.exists():
            st.error(
                "Sample dataset not found. "
                "Place sample_sales.csv inside the data folder."
            )
            st.stop()

        raw_data = load_sample_data(str(DATA_FILE))
        source_name = "Sample sales dataset"

    df = prepare_data(raw_data)

except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as error:
    st.error(f"Unable to process the dataset: {error}")
    st.stop()

except OSError as error:
    st.error(f"Unable to read the file: {error}")
    st.stop()


st.sidebar.success(f"Loaded: {source_name}")

st.sidebar.caption(
    f"Valid records: {len(df)}"
)


# --------------------------------------------------
# 5. SIDEBAR FILTERS
# --------------------------------------------------

st.sidebar.header("Filter Sales")

minimum_date = df["order_date"].min().date()
maximum_date = df["order_date"].max().date()

selected_dates = st.sidebar.date_input(
    "Order date range",
    value=(minimum_date, maximum_date),
    min_value=minimum_date,
    max_value=maximum_date,
)

regions = sorted(df["region"].astype(str).unique())
categories = sorted(df["category"].astype(str).unique())

selected_regions = st.sidebar.multiselect(
    "Select region",
    options=regions,
    default=regions,
)

selected_categories = st.sidebar.multiselect(
    "Select category",
    options=categories,
    default=categories,
)

if len(selected_dates) != 2:
    st.info("Please select both a start date and an end date.")
    st.stop()

start_date, end_date = selected_dates

if start_date > end_date:
    st.error("The start date must be before the end date.")
    st.stop()

filtered_df = df[
    (df["order_date"].dt.date >= start_date)
    & (df["order_date"].dt.date <= end_date)
    & (df["region"].isin(selected_regions))
    & (df["category"].isin(selected_categories))
].copy()


# --------------------------------------------------
# 6. CALCULATE KEY PERFORMANCE INDICATORS
# --------------------------------------------------

st.subheader("Business Overview")

if filtered_df.empty:
    st.warning(
        "No sales records match these filters. "
        "Change your date range or selections."
    )
    st.stop()

total_revenue = filtered_df["revenue"].sum()
total_profit = filtered_df["profit"].sum()
total_orders = filtered_df["order_id"].nunique()

total_units = filtered_df["quantity"].sum()

profit_margin = (
    (total_profit / total_revenue) * 100
    if total_revenue != 0
    else 0
)

average_order_value = (
    total_revenue / total_orders
    if total_orders != 0
    else 0
)

col1, col2, col3 = st.columns(3)

col1.metric(
    "Total Revenue",
    f"₹{total_revenue:,.2f}"
)

col2.metric(
    "Total Profit",
    f"₹{total_profit:,.2f}"
)

col3.metric(
    "Total Orders",
    f"{total_orders:,}"
)

col4, col5, col6 = st.columns(3)

col4.metric(
    "Profit Margin",
    f"{profit_margin:.2f}%"
)

col5.metric(
    "Units Sold",
    f"{total_units:,.0f}"
)

col6.metric(
    "Average Order Value",
    f"₹{average_order_value:,.2f}"
)


# --------------------------------------------------
# 7. PREPARE CHART DATA
# --------------------------------------------------

st.divider()

st.subheader("Sales Performance")

chart_data = filtered_df.copy()

chart_data["month"] = (
    chart_data["order_date"]
    .dt.to_period("M")
    .astype(str)
)

monthly_sales = (
    chart_data.groupby("month", as_index=False)
    .agg(
        Revenue=("revenue", "sum"),
        Profit=("profit", "sum"),
    )
    .sort_values("month")
)

region_sales = (
    chart_data.groupby("region", as_index=False)
    .agg(Revenue=("revenue", "sum"))
    .sort_values("Revenue", ascending=False)
)

category_sales = (
    chart_data.groupby("category", as_index=False)
    .agg(Revenue=("revenue", "sum"))
    .sort_values("Revenue", ascending=False)
)


# --------------------------------------------------
# 8. MONTHLY SALES TREND
# --------------------------------------------------

st.subheader("Monthly Revenue and Profit")

fig_monthly = px.line(
    monthly_sales,
    x="month",
    y=["Revenue", "Profit"],
    markers=True,
    labels={
        "month": "Month",
        "value": "Amount (₹)",
        "variable": "Metric",
    },
    template="plotly_white",
)

fig_monthly.update_layout(
    legend_title_text="Metric",
    hovermode="x unified",
)

st.plotly_chart(
    fig_monthly,
    use_container_width=True
)


# --------------------------------------------------
# 9. REGION AND CATEGORY CHARTS
# --------------------------------------------------

left_chart, right_chart = st.columns(2)

with left_chart:
    st.subheader("Revenue by Region")

    fig_region = px.bar(
        region_sales,
        x="region",
        y="Revenue",
        text_auto=".2s",
        labels={
            "region": "Region",
            "Revenue": "Revenue (₹)",
        },
        template="plotly_white",
    )

    st.plotly_chart(
        fig_region,
        use_container_width=True
    )

with right_chart:
    st.subheader("Revenue by Category")

    fig_category = px.pie(
        category_sales,
        names="category",
        values="Revenue",
        hole=0.45,
    )

    st.plotly_chart(
        fig_category,
        use_container_width=True
    )


# --------------------------------------------------
# 10. TOP-SELLING PRODUCTS
# --------------------------------------------------

st.divider()

st.subheader("Top Products")

product_sales = (
    filtered_df.groupby("product", as_index=False)
    .agg(
        Units_Sold=("quantity", "sum"),
        Revenue=("revenue", "sum"),
        Profit=("profit", "sum"),
    )
    .sort_values("Revenue", ascending=False)
)

st.dataframe(
    product_sales,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Units_Sold": st.column_config.NumberColumn(
            "Units Sold",
            format="%.0f"
        ),
        "Revenue": st.column_config.NumberColumn(
            "Revenue",
            format="₹%.2f"
        ),
        "Profit": st.column_config.NumberColumn(
            "Profit",
            format="₹%.2f"
        ),
    }
)


# --------------------------------------------------
# 11. SALES RECORDS TABLE
# --------------------------------------------------

st.divider()

st.subheader("Sales Records")

display_columns = [
    "order_id",
    "order_date",
    "product",
    "category",
    "region",
    "quantity",
    "unit_price",
    "unit_cost",
    "revenue",
    "profit",
    "sales_rep",
]

st.dataframe(
    filtered_df[display_columns].sort_values(
        "order_date",
        ascending=False
    ),
    use_container_width=True,
    hide_index=True,
)


# --------------------------------------------------
# 12. DOWNLOAD FILTERED DATA
# --------------------------------------------------

csv_data = filtered_df[display_columns].to_csv(
    index=False
).encode("utf-8")

st.download_button(
    label="⬇️ Download Filtered Sales as CSV",
    data=csv_data,
    file_name="filtered_sales_report.csv",
    mime="text/csv",
)

st.caption(
    "Sales Analytics Dashboard | Built with Python, "
    "Streamlit, Pandas, and Plotly"
)
