# Import the libraries
import json
from dash import Dash, html, dcc, callback, Output, Input, dash_table
import plotly.express as px
import pandas as pd
import dash_leaflet as dl
import geopandas
import dash_leaflet.express as dlx
import dash_bootstrap_components as dbc
from dash_extensions.javascript import assign
from xgboost import XGBRegressor
import joblib

# Initiate xgb
temp_model_xgb = XGBRegressor()

# Load dataframes
df_map = pd.read_excel('./Data/daftar_wmoid.xlsx') # UPT Dataframe
ina_nwp_input = pd.read_csv('./Data/MONAS-input_nwp_compile.csv') # Feature to predict from INA-NWP

df_map = df_map.rename(columns={'WMOID': 'lokasi'}) # WMOID dataframe preproceses
df_map = df_map[['lokasi', 'Nama UPT']]



# Make merged dataframe for mapping
df_map = df_map.merge(ina_nwp_input, on='lokasi')
df_map = df_map[['lokasi', 'Nama UPT', 'LON', 'LAT']].drop_duplicates()



# INA-NWP input preprocess
ina_nwp_input = ina_nwp_input.drop(columns=['LAT', 'LON'])  
ina_nwp_input = ina_nwp_input.rename(
    columns={
        'suhu2m(degC)' : 'suhu2m.degC.',
        'dew2m(degC)' : 'dew2m.degC.',
        'rh2m(%)' : 'rh2m...',
        'wspeed(m/s)' : 'wspeed.m.s.',
        'wdir(deg)' : 'wdir.deg.',
        'lcloud(%)' : 'lcloud...',
        'mcloud(%)' : 'mcloud...' ,
        'hcloud(%)' : 'hcloud...',
        'surpre(Pa)' : 'surpre.Pa.' ,
        'clmix(kg/kg)' : 'clmix.kg.kg.' ,
        'wamix(kg/kg)' : 'wamix.kg.kg.' ,
        'outlr(W/m2)' : 'outlr.W.m2.' ,
        'pblh(m)' : 'pblh.m.',
        'lifcl(m)' : 'lifcl.m.' ,
        'cape(j/kg)' : 'cape.j.kg.' ,
        'mdbz' : 'mdbz' ,
        't950(degC)' : 't950.degC.' ,
        'rh950(%)' : 'rh950...',
        'ws950(m/s)' : 'ws950.m.s.' ,
        'wd950(deg)' : 'wd950.deg.' ,
        't800(degC)' : 't800.degC.' ,
        'rh800(%)' : 'rh800...' ,
        'ws800(m/s)' : 'ws800.m.s.',
        'wd800(deg)' : 'wd800.deg.' ,
        't500(degC)' : 't500.degC.' ,
        'rh500(%)' : 'rh500...' ,
        'ws500(m/s)' : 'ws500.m.s.' ,
        'wd500(deg)' : 'wd500.deg.',
})



# Load ML Models
# etr = pickle.load(open('weather_extra_trees_regressor.pkl', 'rb'))
temp_model_xgb.load_model("./models/Temp_xgb_tuned_R2_77.json")


print(ina_nwp_input.columns)
temp_pred = temp_model_xgb.predict(ina_nwp_input.drop(columns=['Date', 'lokasi', 'lcloud...','mcloud...', 'hcloud...', 'clmix.kg.kg.', 'wamix.kg.kg.', 'prec_nwp']))




#OUTPUT TEMP
df_pred_temp = pd.concat([ina_nwp_input['Date'], ina_nwp_input[['lokasi', 'suhu2m.degC.']], pd.Series(temp_pred, index = ina_nwp_input.index)], axis=1)
df_pred_temp.columns = ['Date','lokasi', 'suhu2m.degC.', 'prediction']
df_pred_temp = df_pred_temp.dropna()




# Load script 
temp_colorscale = [
    'rgb(0, 10, 112)',
    'rgb(0, 82, 190)', 
    'rgb(51, 153, 255)', 
    'rgb(153, 235, 255)', 
    'rgb(204, 255, 255)',
    'rgb(255, 255, 204)',
    'rgb(255, 225, 132)',
    'rgb(255, 158, 20)',
    'rgb(245, 25, 25)',
    'rgb(165, 0, 0)',
    'rgb(50, 0, 0)'
    ]

chroma = "https://cdnjs.cloudflare.com/ajax/libs/chroma-js/2.1.0/chroma.min.js"  # js lib used for colors



# Min and Max temp for point colors
temp_min = 0
temp_max = 38


colorbar = dl.Colorbar(id = 'map-colorbar',colorscale=temp_colorscale, width=20, height=150, min=temp_min, max=temp_max, unit='°C')
# humid_colorbar = dl.Colorbar(colorscale=humid_colorscale, width=20, height=150, min=humid_min, max=humid_max, unit='%')

BMKG_LOGO = "https://cdn.bmkg.go.id/Web/Logo-BMKG-new.png"



# Function for adding some properties to all the points in Leaflet Map
on_each_feature = assign(
    """function(feature, layer, context){
        if(feature.properties.lokasi){
            layer.bindTooltip(`${feature['properties']['Nama UPT']} \nKode:${feature['properties']['lokasi']} \n Koord : (${feature['properties']['LAT']},${feature['properties']['LON']})`)
        }
    }
    """)



# Function for assignng circlemarkers to each point
point_to_layer = assign(
    """
    function(feature, latlng, context){
        const {min, max, colorscale, circleOptions, colorProp} = context.hideout;
        const csc = chroma.scale(colorscale).domain([min, max]);  // chroma lib to construct colorscale
        circleOptions.fillColor = csc(feature.properties[colorProp]);  // set color based on color prop
        return L.circleMarker(latlng, circleOptions);  // render a simple circle marker
    }
    """)




# Make dataframe for showing min, max, avg temperature
data_table_lokasi = df_pred_temp.groupby('lokasi')['prediction'].agg(['max', 'mean', 'min']).astype('float64').round(1)
data_table_lokasi = df_map.merge(data_table_lokasi, left_on='lokasi', right_index=True)
data_table_lokasi = data_table_lokasi.rename(columns={'mean': 'average temp', 'max': 'max temp', 'min': 'min temp'})





# Make geopandas geometry for coordinates
geometry = geopandas.points_from_xy(df_map.LON, df_map.LAT)
upt_gpd = geopandas.GeoDataFrame(df_map, geometry=geometry)
upt_gpd = pd.merge(upt_gpd, data_table_lokasi[['lokasi', 'average temp']], on='lokasi')
upt_gpd = upt_gpd.reset_index(drop=True)

geojson = json.loads(upt_gpd.to_json())
geobuf = dlx.geojson_to_geobuf(geojson)
upt = dl.GeoJSON(
    data=geobuf,
    id='geojson',
    format='geobuf',
    zoomToBounds=True,  # when true, zooms to bounds when data changes
    pointToLayer=point_to_layer,  # how to draw points
    onEachFeature=on_each_feature,  # add (custom) tooltip
    hideout=dict(
        colorProp='average temp', 
        circleOptions=dict(
            fillOpacity=1, 
            stroke=False, 
            radius=5),
            min=temp_min, 
            max=temp_max, 
            colorscale=temp_colorscale
            )
)
print('upt_gpd\n', upt_gpd)



# Sort the data by Date
# ina_nwp_input_sorted = ina_nwp_input_filtered.copy()
# ina_nwp_input_sorted = ina_nwp_input_sorted.sort_values(by='Date')

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


# Begin
app = Dash(__name__, external_scripts=[chroma],  external_stylesheets=external_stylesheets, prevent_initial_callbacks=True)

app.layout = html.Div([
    dbc.Container(
        [
            html.A(
                # Use row and col to control vertical alignment of logo / brand
                [dbc.Row(
                    [
                        dbc.Col(html.Img(src=BMKG_LOGO, height="55px")),
                        dbc.Col(dbc.NavbarBrand(className="ms-2")),
                        
                    ],
                    align="center",
                    className="g-0 d-flex flex-column align-items-center justify m-2",
                ),
                html.H1(children='MONAS Dashboard'),
                ],
                href="#",
                style={
                    "textDecoration": "none",
                    "display" : "flex",
                    "align-content": "center",
                    "justify-content" : "center",
                    "flex-direction" : "row",
                    },
            ),
        ]
    ),

    # dcc.Dropdown(id='model-list',
    #             options=[
    #                 {'label': i, 'value': i} for i in files
    #             ],
    #             multi=True
    # ),

    html.Div([
        html.Div([  # Wrap the map and header in a div for layout
            dl.Map(
                [
                    dl.TileLayer(), 
                    dl.ScaleControl(position="bottomleft"),
                    dl.FullScreenControl(),
                    upt,
                    colorbar,
                ],
                center=[-2.058210136999589, 116.78386542384145],
                markerZoomAnimation = True,
                id = 'dash-leaflet-map',
                style={
                    'height': '90vh', 
                    'width' : '50vw'
                    }
                ),
            html.Div([
                html.Div([
                    html.Div([ # Div for map, metric, and graph
                        html.Div([
                            dcc.Loading(
                                dcc.Graph(
                                    id='graph_per_loc',
                                    figure={
                                        'layout' : {
                                            "xaxis": {
                                            "visible": False
                                            },
                                            "yaxis": {
                                                "visible": False
                                            },
                                            "annotations": [
                                                {
                                                    "text": "Click on one of the Station in the map to view graph.",
                                                    "xref": "paper",
                                                    "yref": "paper",
                                                    "showarrow": False,
                                                    "font": {
                                                        "size": 28
                                                    }
                                                }
                                            ]
                                        }
                                    } 
                                ),
                            ),
                            dcc.RangeSlider(
                                id='graph-metric',
                                min=0,
                                max=40,
                                value=[0,0],
                                step=None,
                                vertical=False,
                                tooltip={
                                    "placement": "bottom", 
                                    "always_visible": True
                                    },
                                disabled=True,
                            ),
                            
                        ]),
                    ], 
                    style={
                        'display': 'grid', 
                        'grid-column': 'auto auto',
                        'grid-auto-flow': 'column'
                    }),
                ], 
                style={
                    'display': 'grid', 
                    'grid-column': 'auto auto',
                    'grid-auto-flow': 'row'
                    }
                ),  # Display elements side by side
            ]),
        ], 
        style={
            'display' : 'grid',
            'grid-column': 'auto auto',
            'grid-auto-flow': 'column'
            }),
        html.Div([# Div for other details such as comparison graph, data tables, and other metrics 
                dash_table.DataTable(
                    data=data_table_lokasi.to_dict('records'), 
                    page_size=10)       
                ], 
                style= {
                    'display': 'grid', 
                    'grid-column': 'auto auto',
                    'grid-auto-flow': 'row'
                }
                ),
    ])
])



def plot_graph(df_graph, upt_name, nwp_output, graph_type):
    figure = px.line(
            df_graph, 
            x='Date', 
            y='prediction', 
            title=f'{graph_type} in UPT {upt_name} (UTF)', 
            markers=True, 
            line_shape='spline'
            )
    
    figure.add_scatter(
            x=df_graph['Date'], 
            y=df_graph[nwp_output], 
            mode='lines', 
            name=f'Output {type} 2m INA-NWP',
            line_shape='spline'
            )
    
    figure.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            )
        )
    
    return figure



def get_datatable(wmoid_lokasi, prop_lokasi, column):
    return data_table_lokasi[wmoid_lokasi == prop_lokasi][column].iloc[0]



# Callback function for changing 
@callback(
        Output("graph-metric", "value"), # RangeSlider value
        Output("graph-metric", "min"), # RangeSlider minimum value
        Output("graph-metric", "max"), # RangeSlider maximum value
        Output("graph_per_loc", "figure"), # Graph Figure

        Input ("geojson", "clickData"), # Marker OnClick Event
        prevent_initial_call=True
        )
def upt_click(feature):
    print(feature)    
    if feature is not None:
        wmoid_lokasi = data_table_lokasi['lokasi']
        prop_lokasi = feature['properties']['lokasi']
        nama_upt = data_table_lokasi[wmoid_lokasi == prop_lokasi]['Nama UPT'].values[0]

        # Column to display on plots
        temp_features_to_display = ['Date', 'suhu2m.degC.', 'prediction', 'lokasi']

        # Sliced Dataframe filtered to only one location
        dff_one_loc_temp = df_pred_temp[df_pred_temp['lokasi'] == prop_lokasi][temp_features_to_display]

        # Plotly Express Figure for  Temperature
        type = 'Temperature'
        figure = plot_graph(dff_one_loc_temp, nama_upt, 'suhu2m.degC.', type)

        # Min - Max Value for Inactive Temperature Slider
        min = get_datatable(wmoid_lokasi, prop_lokasi, 'min temp')
        avg = get_datatable(wmoid_lokasi, prop_lokasi, 'average temp')
        max = get_datatable(wmoid_lokasi, prop_lokasi, 'max temp')

        # Hideout dict
        min_abs = temp_min
        max_abs = temp_max

        # Combining the value to one array
        slider_value = [min, max]
        

        return (slider_value, min_abs, max_abs, figure)

if __name__ == '__main__':
    app.run_server(host= '0.0.0.0',debug=False)
