# Import Libraries
import npf as npf
import streamlit as st
import pandas as pd
import numpy_financial as npf
import sqlite3
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode, JsCode
from streamlit_folium import folium_static
import folium
import plotly.express as px


# Set Page Width
st.set_page_config(layout="wide")

# Clean CSV, return dataframe
def clean_data():

    # Load CSV
    df = pd.read_csv("zillow_philly_data.csv", header=0, index_col=False)

    # Delete, rename columns
    df.drop(columns=['parentRegion', 'mortgageRates', 'datePriceChanged', 'timeOnZillow'], inplace=True)
    df.rename(columns={'address/city': 'city', 'address/state': 'state',
                       'address/streetAddress': 'address', 'address/zipcode': 'zipcode',
                       'listing_sub_type/is_FSBA': 'is_fsba', 'listing_sub_type/is_FSBO': 'is_fsbo',
                       'listing_sub_type/is_bankOwned': 'is_bankOwned',
                       'listing_sub_type/is_comingSoon': 'is_comingSoon',
                       'listing_sub_type/is_forAuction': 'is_forAuction',
                       'listing_sub_type/is_foreclosure': 'is_foreclosure',
                       'listing_sub_type/is_newHome': 'is_newHome', 'listing_sub_type/is_openHouse': 'is_openHouse',
                       'listing_sub_type/is_pending': 'is_pending', 'mortgageRates/arm5Rate': 'arm5_rate',
                       'mortgageRates/fifteenYearFixedRate': '15fixed_rate',
                       'mortgageRates/thirtyYearFixedRate': '30fixed_rate',
                       'parentRegion/name': 'region', 'rentZestimate': 'restimate'}, inplace=True)
    pd.set_option('display.max_columns', None)

    # Create zpid column from url
    df['zpid'] = df['url'].str.extract('((?<=\/)\d*(?=_zpid))')
    zpid_column = df.pop('zpid')
    df.insert(0, 'zpid', zpid_column)

    # Convert data types
    df['zpid'] = df['zpid'].astype(int)
    df['is_openHouse'] = df['is_openHouse'].astype(bool)
    df['yearBuilt'] = df['yearBuilt'].fillna(0).astype(int)
    df['taxAssessedYear'] = df['taxAssessedYear'].fillna(0).astype(int)
    # df['daysOnZillow'] = df['daysOnZillow'].fillna(200).astype(int)
    df['daysOnZillow'].fillna(value=df['daysOnZillow'].mean(), inplace=True)
    df['price'] = df['price'].astype(float)
    df['priceChange'] = df['priceChange'].fillna(0).astype(float)
    df['zestimate'] = df['zestimate'].fillna(0).astype(float)
    df['restimate'] = df['restimate'].fillna(0).astype(float)
    df['taxAssessedValue'] = df['taxAssessedValue'].fillna(0).astype(float)
    df['monthlyHoaFee'] = df['monthlyHoaFee'].fillna(0).astype(float)

    return df


# Initialize database, create tables and schema
def init_db(dataframe, connection, cursor):
    # Create master table from cleaned dataframe
    dataframe.to_sql('master_table', connection, if_exists ='replace', index = False)
    connection.commit()

    # Drop table if exists, create table with constraints, insert data from master table, commit to conn

    # PAGE TABLE

    cursor.execute("""DROP TABLE IF EXISTS page""")

    cursor.execute("""
    CREATE TABLE page (
    url TEXT PRIMARY KEY NOT NULL,
    daysOnZillow INTEGER,
    pageViewCount INTEGER,
    favoriteCount INTEGER
    );
    """)

    cursor.execute(
    """
    INSERT INTO page (url, daysOnZillow, pageViewCount, favoriteCount)
    SELECT url, daysOnZillow, pageViewCount, favoriteCount FROM master_table"""
    )

    connection.commit()

    # ADDRESS TABLE

    cursor.execute("""DROP TABLE IF EXISTS address""")

    cursor.execute("""
    CREATE TABLE address (
    address_id INTEGER PRIMARY KEY ASC,
    city TEXT,
    state TEXT, 
    address TEXT,
    zipcode INTEGER, 
    region TEXT
    );
    """)

    cursor.execute(
    """
    INSERT INTO address (city, state, address, zipcode, region)
    SELECT city, state, address, zipcode, region FROM master_table"""
    )

    connection.commit()

    # PHYSICAL TABLE

    cursor.execute("""DROP TABLE IF EXISTS physical""")

    cursor.execute("""
    CREATE TABLE physical (
    physical_id INTEGER PRIMARY KEY ASC,
    bedrooms REAL,
    bathrooms REAL,
    livingArea REAL,
    latitude REAL,
    longitude REAL,
    yearBuilt INTEGER,
    homeType TEXT,
    homeStatus TEXT,
    isNonOwnerOccupied INTEGER,
    is_fsba INTEGER,
    is_fsbo INTEGER,
    is_bankOwned INTEGER,
    is_comingSoon INTEGER,
    is_forAuction INTEGER,
    is_foreclosure INTEGER,
    is_newHome INTEGER,
    is_openHouse INTEGER,
    is_pending INTEGER
    );
    """)

    cursor.execute(
    """
    INSERT INTO physical (bedrooms, bathrooms, livingArea, latitude, longitude, yearBuilt, homeType,homeStatus, 
    isNonOwnerOccupied, is_fsba, is_fsbo, is_bankOwned, is_comingSoon, is_forAuction,
    is_foreclosure, is_newHome, is_openHouse, is_pending)
    SELECT bedrooms, bathrooms, livingArea, latitude, longitude, yearBuilt, homeType,homeStatus, isNonOwnerOccupied,
    is_fsba, is_fsbo, is_bankOwned, is_comingSoon, is_forAuction,
    is_foreclosure, is_newHome, is_openHouse, is_pending FROM master_table"""
    )

    connection.commit()

    # FINANCIAL TABLE

    cursor.execute("""DROP TABLE IF EXISTS financial""")

    cursor.execute("""
    CREATE TABLE financial (
    financial_id INTEGER PRIMARY KEY ASC,
    price REAL,
    zestimate REAL,
    restimate REAL,
    priceChange REAL,
    taxAssessedValue REAL,
    taxAssessedYear INTEGER,
    monthlyHoaFee REAL,
    "30fixed_rate" REAL,
    "15fixed_rate" REAL
    );
    """)

    cursor.execute(
    """
    INSERT INTO financial (price, zestimate, restimate, priceChange, taxAssessedValue,
    TaxAssessedYear, monthlyHoaFee, "30fixed_rate", "15fixed_rate")
    SELECT price, zestimate, restimate, priceChange, taxAssessedValue,
    TaxAssessedYear, monthlyHoaFee, "30fixed_rate", "15fixed_rate" FROM master_table"""
    )

    connection.commit()

    # ZP TABLE

    cursor.execute("""DROP TABLE IF EXISTS zp""")

    cursor.execute("""
    CREATE TABLE zp (
    ID INTEGER UNIQUE PRIMARY KEY ASC,
    zpid INTEGER,
    url TEXT,
    address_id INTEGER,
    physical_id INTEGER,
    financial_id INTEGER,
    FOREIGN KEY (url) REFERENCES page (url) ON UPDATE CASCADE,
    FOREIGN KEY (address_id) REFERENCES address (address_id) ON UPDATE CASCADE,
    FOREIGN KEY (physical_id) REFERENCES physical (physical_id) ON UPDATE CASCADE,
    FOREIGN KEY (financial_id) REFERENCES financial (financial_id) ON UPDATE CASCADE
    );
    """)

    cursor.execute(
    """
    INSERT INTO zp (zpid, url)
    SELECT zpid, url FROM master_table;
    """
    )

    cursor.execute(
    """
    UPDATE zp 
    SET address_id = (
    SELECT address_id
    FROM address
    WHERE ID = address_id)
    """
    )

    cursor.execute(
    """
    UPDATE zp 
    SET physical_id = (
    SELECT physical_id
    FROM physical
    WHERE ID = physical_id)
    """
    )

    cursor.execute(
    """
    UPDATE zp 
    SET financial_id = (
    SELECT financial_id
    FROM financial
    WHERE ID = financial_id)
    """
    )


    connection.commit()


# Return table's corresponding dataframes (for streamlit interactive compatibility)
def get_dfs(connector):
    df1 = pd.read_sql("SELECT * FROM address", con=connector)
    df2 = pd.read_sql("SELECT * FROM financial", con=connector)
    df3 = pd.read_sql("SELECT * FROM page", con=connector)
    df4 = pd.read_sql("SELECT * FROM physical", con=connector)
    df5 = pd.read_sql("SELECT * FROM zp", con=connector)
    df6 = pd.read_sql("SELECT * FROM master_table", con=connector)
    return df1, df2, df3, df4, df5, df6

# Reorganize Columns for Grid, return organized df
def reorganize_columns(df):
    df = df[['zpid', 'price', 'bathrooms', 'bedrooms', 'livingArea', 'homeStatus',
               'homeType', 'city', 'state', 'address', 'zipcode', 'region',
               'zestimate', 'restimate', 'pageViewCount', 'daysOnZillow',
               'favoriteCount', 'isNonOwnerOccupied', 'latitude',
               'is_fsba', 'is_fsbo', 'is_bankOwned', 'is_comingSoon', 'is_forAuction', 'is_foreclosure',
               'is_newHome', 'is_openHouse', 'is_pending', 'longitude', 'monthlyHoaFee', 'arm5_rate', '15fixed_rate',
               '30fixed_rate', 'priceChange', 'propertyTaxRate',
               'restimateHighPercent', 'restimateLowPercent', 'taxAssessedValue', 'taxAssessedYear', 'url', 'yearBuilt',
               'zestimateHighPercent', 'zestimateLowPercent']]
    return df


def create_grid(dfs):

    gb = GridOptionsBuilder.from_dataframe(dfs)

    # Table configurations (sending to gridOptions dictionary)

    # Hiding columns
    hidden_columns = [ "isNonOwnerOccupied", "latitude", "longitude", "is_fsba", "is_fsbo", "is_bankOwned",
                      "is_comingSoon", "is_forAuction", "is_foreclosure", "is_newHome", "is_openHouse",
                      "is_pending", "monthlyHoaFee", "arm5_rate", "15fixed_rate", "30fixed_rate", "propertyTaxRate",
                      "restimateHighPercent", "restimateLowPercent", "taxAssessedValue", "taxAssessedYear",
                      "zestimateHighPercent", "zestimateLowPercent", "url", "zipcode", "address"]
    # Column Configurations, Naming Headers
    gb.configure_columns(hidden_columns, editable=False, hide=True)
    gb.configure_columns("zpid",pinned = "left", headerName = "ZPID")
    gb.configure_columns("price", headerName="Price")
    gb.configure_columns("bathrooms", headerName="Bathrooms")
    gb.configure_columns("bedrooms", headerName="Bedrooms")
    gb.configure_columns("livingArea", headerName="Living Area (sqft)")
    gb.configure_columns("homeStatus", headerName="Home Status")
    gb.configure_columns("homeType", headerName="Home Type")
    gb.configure_columns("city", headerName="City")
    gb.configure_columns("state", headerName="State")
    gb.configure_columns("region", headerName="Region")
    gb.configure_columns("zestimate", headerName="Market Value (estimate)")
    gb.configure_columns("restimate", headerName="Rental Value (estimate)")
    gb.configure_columns("pageViewCount", headerName="Page Views")
    gb.configure_columns("daysOnZillow", headerName="Days On Zillow")
    gb.configure_columns("favoriteCount", headerName="Favorite Count")
    gb.configure_columns("yearBuilt", headerName="Year Built")

    #Grid Configurations
    gb.configure_selection('single', use_checkbox=False)
    gb.configure_grid_options(copyHeadersToClipboard=True, enableCellTextSelection=True, ensureDomOrder=True,
                              suppressCopyRowsToClipboard=True, rowHeight=38, headerHeight = 50, floatingFilter = True)
    gb.configure_side_bar(True,False)
    go = gb.build()

    # Uses the gridOptions dictionary to generate table
    with st.expander("Property Browser", expanded=True):
        AgGrid(dfs, gridOptions=go, updatallow_unsafe_jscode=True, data_return_mode='AS_INPUT',
               update_mode=GridUpdateMode.NO_UPDATE, enable_enterprise_modules=True, allow_unsafe_jscode=True)

        # Get input from user
        zpid_input = st.number_input('Paste the property zpid# here!', None, None, 10429543,
                                     help="Right-click to copy/paste a zpid from the grid above")
        df_input = dfs.loc[dfs['zpid'] == zpid_input]
        df_input.reset_index(drop=True, inplace=True)
        #st.write(df_input.head())
        return df_input


def create_st_interface(df_input):
    try:
        with st.sidebar:
            st.title("Investment Calculator")
            try:
                st.caption(df_input['address'][0] +" " +  df_input['city'][0]+", "
                           +  df_input['state'][0] + " " +str(df_input['zipcode'][0]))
                st.caption("[Look at the property on zillow](%s)" % df_input['url'][0])
            except:
                print(None)
            # Purchase/Rehab Sub-Section
            st.header('Purchase/Rehab')

            # Input gathered from selected row

            price_input = df_input['price'][0]
            if price_input == 0 and df_input['zestimate'][0] != 0:
                price_slider = st.slider("Purchase Price", min_value=int(df_input['zestimate'][0] * .3),
                                         max_value=int(df_input['zestimate'][0] * 1.5),
                                         value=int(df_input['zestimate'][0]), format="$%d", step=100)
            elif price_input == 0 and df_input['zestimate'][0] == 0:
                price_slider = st.slider("Purchase Price", min_value=int(0),
                                         max_value=int(3000000), value=int(200000), format="$%d",
                                         step=1000)

            elif price_input != 0:
                price_slider = st.slider("Purchase Price", min_value=int(price_input * .3),
                                         max_value=int(price_input * 1.5), value=int(price_input), format="$%d", step=100)

            zestimate_input = df_input['zestimate'][0]
            if zestimate_input == 0:
                zestimate_slider = st.slider("Market Value / ARV (Zestimate)", min_value=int(price_input * .5),
                                             max_value=int(price_input * 1.5), value=int(price_input), format="$%d")
            elif zestimate_input != 0:
                zestimate_slider = st.slider("Market Value / ARV (Zestimate)", min_value=int(zestimate_input * .5),
                                             max_value=int(zestimate_input * 1.5), value=int(zestimate_input), format="$%d", step=100)

            # Input directly from user

            rehab_input = st.number_input("Rehab Costs $", min_value=None, max_value=None, value=0)
            apg_input = st.number_input("Annual Property Growth %", min_value=None, max_value=None, value=2.0, step = .1) * .01
            closing_cost_input = st.number_input("Closing Costs %", min_value=None, max_value=None, value=5.0, step = .1) * .01

            # Loan Details Sub-Section
            st.header('Loan Details')

            # Input directly from user

            down_payment_input = st.slider("Down Payment $", min_value=0,
                                           max_value=price_slider, value=int(price_slider * .2),format="$%d", step=10)
            dp_perc = (down_payment_input / price_input) * 100
            st.caption(str("{:.2f}".format(dp_perc)) + " % Of Purchase Price")

            interest_rate_input = st.number_input("Interest Rate %", min_value=None, max_value=None, value=2.00,
                                                  step=.1) * .01
            loan_term_input = st.radio("Loan Term", ("15 Year", "30 Year", "Arm5"), index=1)
            if loan_term_input == "15 Year":
                loan_term = 15
            elif loan_term_input == "30 Year":
                loan_term = 30
            elif loan_term_input == "Arm5":
                loan_term = 5

            # Expenses/Income Input
            st.header('Monthly Expenses/Income')

            # Input gathered from selected row
            restimate_input = df_input['restimate'][0]
            if restimate_input == 0:
                restimate_slider = st.slider("Rental Income (Monthly)", min_value= 0,
                                             max_value= int(zestimate_slider *1.8), value=int(restimate_input), format="$%d", step = 20)
            elif restimate_input != 0:
                restimate_slider = st.slider("Rental Income (Monthly)", min_value=0,
                                             max_value=int(restimate_input * 2), value=int(restimate_input), format="$%d", step=20)

            taxAssessedValue_input = df_input['taxAssessedValue'][0]
            if taxAssessedValue_input == 0:
                taxAssessedValue_input_slider = st.slider("Tax Assessed Value ", min_value=int(zestimate_slider * .5),
                                                          max_value=int(zestimate_slider * 1.2 + 1),
                                                          value=int(zestimate_slider), format="$%d", step=100)
            elif taxAssessedValue_input != 0:
                taxAssessedValue_input_slider = st.slider("Tax Assessed Value",
                                                          min_value=int(taxAssessedValue_input * .5),
                                                          max_value=int(taxAssessedValue_input * 1.5),
                                                          value=int(taxAssessedValue_input), format="$%d", step=100)

            property_tax_input = (taxAssessedValue_input_slider * .0098) / 12
            st.caption("$" + str("{:.0f}".format(property_tax_input)) + " in tax payments per month")

            # Input gathered from user
            insurance_input = st.number_input("Monthly Insurance ($ a Month) ", min_value=None, max_value=None,
                                              value=110)
            maintenance_input = st.number_input("Maintenance/Repair Costs (% of Rental Income) ", min_value=None,
                                                max_value=None, value=11.0, step= .1) * .01
            st.caption("$" + str("{:.0f}".format(maintenance_input * restimate_slider)) + " /month")
            capex_input = st.number_input("Capital Expenditures (% of Rental Income) ", min_value=None, max_value=None,
                                          value=10.0, step= .1) *.01
            st.caption("$" + str("{:.0f}".format(capex_input * restimate_slider)) + " /month")
            vacancy_input = st.number_input("Vacancy Expenses (% of Rental Income) ", min_value=None, max_value=None,
                                            value=5.0, step=.1) * .01
            st.caption("$" + str("{:.0f}".format(vacancy_input * restimate_slider)) + " /month")
            management_input = st.number_input("Management Fees (% of Rental Income) ", min_value=None, max_value=None,
                                               value=0.0, step = .1) * .01
            st.caption("$" + str("{:.0f}".format(management_input * restimate_slider)) + " /month")
            gas_electric_input = st.number_input("Gas/Electric Bill ($ a Month) ", min_value=None, max_value=None,
                                                 value=0, step=5)
            water_sewer_garbage_input = st.number_input("Water, Sewer, Garbage Bill ($ a Month) ", min_value=None,
                                                        max_value=None, value=80, step = 5)
            hoa_input = st.number_input("Monthly HOA Fee ($ a Month) ", min_value=None, max_value=None,
                                        value=int("{:.0f}".format(df_input['monthlyHoaFee'][0])), step = 5)

            # ALL CALCULATIONS
            cash_invested = (price_slider * closing_cost_input) + down_payment_input + rehab_input

            loan_principle = price_slider - down_payment_input

            monthly_mortgage_payment = npf.pmt(interest_rate_input / 12, loan_term * 12, loan_principle, 0)

            gross_operating_expenses = (property_tax_input + insurance_input + gas_electric_input +
                                        water_sewer_garbage_input + hoa_input) + (vacancy_input * restimate_slider) + \
                                       (maintenance_input * restimate_slider) + (management_input * restimate_slider) + \
                                       (capex_input * restimate_slider)

            noi_operating_expenses = (property_tax_input + insurance_input + gas_electric_input +
                                      water_sewer_garbage_input + hoa_input) + (vacancy_input * restimate_slider) + \
                                     (maintenance_input * restimate_slider) + (management_input * restimate_slider)

            total_monthly_payment = (monthly_mortgage_payment * -1) + gross_operating_expenses

            cash_flow = restimate_slider - total_monthly_payment

            noi = restimate_slider - noi_operating_expenses

            c_on_c_return = (cash_flow * 12) / cash_invested * 100

            cap_rate = (noi * 12 / zestimate_slider) * 100

            fifty_p_rule = (restimate_slider * .5) - monthly_mortgage_payment

            fifty_p_rule_bool = False
            if fifty_p_rule > 0:
                fifty_p_rule_bool = True

            two_p_rule = restimate_slider / price_slider * 100

            two_p_rule_bool = False
            if two_p_rule > 2:
                two_p_rule_bool = True
    except KeyError:
        st.caption("This zpid number is invalid")


    try:
        # Display various metrics
        col1, col2, col3, = st.columns((1.5,1.5,1.5))
        col1.metric(label="Cash Flow", value="${:,.0f}".format(cash_flow))
        col2.metric(label="Total Rental Income", value="${:,.0f}".format(restimate_slider))
        col3.metric(label="Total Monthly Payment", value="${:,.0f}".format(total_monthly_payment * -1))
        col3.metric(label="Monthly Mortgage Payment", value="${:,.0f}".format(monthly_mortgage_payment))
        col2.metric(label="NOI", value="${:,.0f}".format(noi))
        col1.metric(label="Total Cash Invested", value="${:,.0f}".format(cash_invested))
        st.write("")
        st.write("")
        colA, colB, colC, colD = st.columns((1,1,1,1))
        colA.metric(label="Capitalization Rate", value="%{:,.2f}".format(cap_rate))
        colB.metric(label="Cash On Cash Return ", value="%{:,.2f}".format(c_on_c_return))
        colC.metric(label="50% Rule ", value=fifty_p_rule_bool, delta="${:,.0f}".format(fifty_p_rule))
        colD.metric(label="2% Rule ", value=two_p_rule_bool, delta="%{:,.1f}".format(two_p_rule))
        st.write("")
        st.write("")

        with st.expander("Visualizations", expanded = True):
            # Plot Expense Chart
            ge_labels = ["Property Tax", "Insurance", "Gas/Electric", "Water/Sewer/Garbage", "HOA Fees", "Vacancy",
                         "Maintenance/Repairs", "Management", "Cap-Ex"]
            ge_values = [property_tax_input, insurance_input, gas_electric_input, water_sewer_garbage_input, hoa_input,
                         (vacancy_input * restimate_slider), (maintenance_input * restimate_slider),
                         (management_input * restimate_slider), (capex_input * restimate_slider)]
            expense_chart = px.pie(names=ge_labels, values=ge_values, hole=.6, color=ge_labels,
                                   color_discrete_sequence=px.colors.sequential.RdBu)
            expense_chart.update_layout(title={
                'text': "Monthly Expense Breakdown", 'y': .985, 'x': .46, 'xanchor': 'center', 'yanchor': 'top'}, width = 800)
            st.plotly_chart(expense_chart)

            # Create appreciation graph for
            year_series = []
            for i in range(1, loan_term + 1):
                year_series.append(i)

            property_appreciation_series = []
            for i in range(1, loan_term + 1):
                i = "${:,.0f}".format(((apg_input + 1) ** i) * zestimate_slider, 0)
                property_appreciation_series.append(i)

            cash_flow_series = []
            for i in range(1, loan_term + 1):
                i = "${:,.0f}".format((((apg_input + 1) ** i) * restimate_slider) - (
                        (((apg_input + 1) ** i) * gross_operating_expenses) + (monthly_mortgage_payment * -1)), 0)
                cash_flow_series.append(i)

            df_appreciate = pd.DataFrame(list(zip(year_series, property_appreciation_series, cash_flow_series)),
                                         columns=['Year', 'Property Value', 'Cash Flow'])

            appreciation_graph = px.line(df_appreciate, x="Year", y="Property Value", hover_data=["Cash Flow"])
            appreciation_graph.update_layout(hovermode='x', title={
                'text': "Property Appreciation Over Loan", 'y': .9, 'x': 0.405, 'xanchor': 'center', 'yanchor': 'top'},
                                             width=930, plot_bgcolor="#ffffff")
            appreciation_graph.update_traces(line_color='#2eb82e', line_width=2)
            appreciation_graph.update_yaxes(nticks=10, linecolor="#d9d9d9")
            appreciation_graph.update_xaxes(linecolor="#d9d9d9", showticklabels=True)
            st.plotly_chart(appreciation_graph)

    except NameError:
        print(None)

    # Map Selected Property
    try:
        with st.expander("Map",True):
            latitude = df_input['latitude'][0]
            longitude = df_input['longitude'][0]
            url = df_input['url'][0]

            # center map
            m = folium.Map(location=[latitude, longitude], zoom_start=16)

            # add marker for Liberty Bell
            tooltip = "{address}<br>" "Price: ${price}<br>" "Bedrooms: {bedrooms}<br>" "Bathrooms: {bathrooms}<br>".format\
                (address = str(df_input['address'][0] + " " + df_input['city'][0] + ", " + df_input['state'][0]),
                 price=int(df_input['price'][0]), bedrooms = df_input['bedrooms'][0], bathrooms = df_input['bathrooms'][0])

            folium.Marker(
                [latitude, longitude], popup=url, tooltip=tooltip
            ).add_to(m)

            # call to render Folium map in Streamlit
            folium_static(m)
    except KeyError:
        print(None)


# Create SQLITE CONNECTION, zillow.db
# MAIN
# Establish connection, cursor
conn = sqlite3.connect('zillow.db')
c = conn.cursor()

# Clean data, get dfs back
df = clean_data()
init_db(df, conn, c)
df_address, df_financial, df_page, df_physical, df_zp, dfs = get_dfs(conn)

dfs = reorganize_columns(dfs)

st.subheader("The Philadelphia Real Estate Assessor")
st.caption("Welcome! Use the property browser to sort through investment properties.")
st.caption("Copy/Paste an individual property's ZPID in the field below to run financial analysis via the Investment Calculator.")

# Create Grid, Get zpid # input and return single row dataframe

df_input = create_grid(dfs)


# Calculator Sidebar, Create Variables
create_st_interface(df_input)


# Text at end
st.caption("")
st.caption("Data last updated from zillow on 4/03/2022")