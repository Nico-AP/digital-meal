import pandas as pd

from bokeh.embed import components
from bokeh.layouts import column
from bokeh.models import RangeTool, BasicTicker, PrintfTickFormatter
from bokeh.palettes import BuGn9
from bokeh.plotting import figure
from bokeh.transform import linear_cmap

from datetime import timedelta


days_de = [
    'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag',
    'Freitag', 'Samstag', 'Sonntag'
]
days_de_short = [
    'Mo', 'Di', 'Mi', 'Do',
    'Fr', 'Sa', 'So'
]
days_en_de = {
    'Monday': 'Montag', 'Tuesday': 'Dienstag',
    'Wednesday': 'Mittwoch', 'Thursday': 'Donnerstag',
    'Friday': 'Freitag', 'Saturday': 'Samstag',
    'Sunday': 'Sonntag'
}
days_en_de_short = {
    'Monday': 'Mo', 'Tuesday': 'Di',
    'Wednesday': 'Mi', 'Thursday': 'Do',
    'Friday': 'Fr', 'Saturday': 'Sa',
    'Sunday': 'So'
}


def get_timeseries_plot(date_series, bin_width=1,
                        date_min=None, date_max=None):
    """
    Create timeseries bar plot.
    :param date_series: Pandas Series of datetime objects and counts.
    :param bin_width: Width of bin in bar plot.
    :param date_min: Minimum date of date range on x-axis - if None
        is provided, minimum of data_series is used.
    :param date_max: Maximum date of date range on x-axis - if None
        is provided, maximum of data_series is used.
    :return: Dictionary containing bokeh script and bokeh plot
        ({'script': script, 'div': div}).
    """
    x_values = date_series.keys().to_list()
    y_values = date_series.values.tolist()

    bin_width = timedelta(days=bin_width)

    if date_min is None:
        date_min = min(date_series.keys())
    if date_max is None:
        date_max = max(date_series.keys())

    x_range = date_max - date_min
    x_upper_bound = date_max + timedelta(days=30)
    x_lower_bound = date_max - timedelta(days=(x_range.days/3) * 2)

    y_max = max(y_values) + (0.05 * max(y_values))

    p = figure(
        x_range=(x_lower_bound, x_upper_bound),
        x_axis_type='datetime',
        height=300,
        toolbar_location=None,
        tools='xpan',
        sizing_mode='stretch_width'
    )
    p.vbar(
        x=x_values,
        top=y_values,
        fill_color='#465ad9',
        line_color='#465ad9',
        width=bin_width
    )
    p.background_fill_color = None
    p.border_fill_color = None
    p.outline_line_color = None
    p.xgrid.grid_line_color = 'white'
    p.xgrid.grid_line_dash = [6, 4]
    p.ygrid.grid_line_color = None
    p.ygrid.band_fill_color = 'orange'
    p.ygrid.band_fill_alpha = 0.5
    p.yaxis.minor_tick_line_color = None
    p.yaxis.major_tick_line_color = None

    p.y_range.start = 0
    p.y_range.end = y_max

    p.yaxis.axis_label = 'Anzahl Videos'
    p.yaxis.axis_label_text_font_style = 'normal'
    p.yaxis.axis_line_color = None
    p.yaxis.axis_label_text_font_size = '20px'
    p.yaxis.major_label_text_font_size = '15px'
    p.xaxis.major_label_text_font_size = '15px'
    p.xaxis.axis_line_color = '#465ad9'
    p.xaxis.major_tick_line_color = 'white'
    p.x_range.bounds = (date_min, date_max)

    select = figure(
        height=70,
        y_range=p.y_range,
        y_axis_type=None,
        x_range=(date_min, date_max),
        x_axis_type='datetime',
        tools='',
        toolbar_location=None,
        sizing_mode='stretch_width'
    )
    range_tool = RangeTool(x_range=p.x_range)
    range_tool.overlay.fill_color = 'white'
    range_tool.overlay.fill_alpha = 0.5

    select.x_range.min_interval = timedelta(days=1)
    select.x_range.max_interval = date_max - date_min
    select.x_range.bounds = (date_min, date_max)

    select.vbar(
        x=x_values,
        top=y_values,
        fill_color='white',
        line_color='white',
        width=bin_width
    )
    select.ygrid.grid_line_color = None
    select.border_fill_alpha = 0
    select.background_fill_color = '#465ad9'
    select.add_tools(range_tool)

    plot = column(p, select, sizing_mode='stretch_width')
    script, div = components(plot)

    return {'script': script, 'div': div}


def get_weekday_use_plot(data):
    dates = pd.Series([d.strftime('%A') for d in data])
    x_labels = dates.value_counts().keys().to_list()
    y_values_abs = dates.value_counts().values.tolist()
    y_values_rel = [v/sum(y_values_abs)*100 for v in y_values_abs]

    df = pd.DataFrame(list(zip(x_labels, y_values_abs, y_values_rel,
                               ['00:00'] * len(x_labels))),
                      columns=['Day', 'Count', 'Rate', 'Dummy'])
    df.replace({'Day': days_en_de}, inplace=True)

    TOOLTIPS = """
        <div style="font-size: 0.8rem; color: #00441B">
            <div>
                <span style="font-weight: bold;">Anzahl Videos: </span>
                <span>@Count</span>
            </div>
            <div>
                <span style="font-weight: bold;">Anteil: </span>
                <span>@Rate%</span>
            </div>
        </div>
    """

    p = figure(
        x_range=days_de,
        y_range=['00:00'],
        x_axis_location=None,
        height=80,
        tools='hover,save,pan,box_zoom,reset,wheel_zoom',
        toolbar_location=None,
        tooltips=TOOLTIPS,
        sizing_mode='stretch_width'
    )

    p.grid.grid_line_color = None
    p.outline_line_color = None
    p.axis.axis_line_color = None
    p.axis.major_tick_line_color = None
    p.axis.major_label_text_font_size = '15px'
    p.yaxis.major_label_text_color = '#FFF0'

    r = p.rect(
        x='Day',
        y='Dummy',
        source=df,
        width=1, height=1,
        fill_color=linear_cmap('Rate', BuGn9[::-1], low=10, high=20),
        line_color=None
    )

    p.add_layout(r.construct_color_bar(
        major_label_text_font_size='9px',
        ticker=BasicTicker(desired_num_ticks=len(BuGn9)),
        formatter=PrintfTickFormatter(format='%d%%'),
        label_standoff=6,
        border_line_color=None,
        background_fill_color=None,
        padding=5
    ), 'right')
    p.border_fill_color = None

    # Disable touch controls
    p.toolbar.active_drag = None
    p.toolbar.active_scroll = None

    script, div = components(p)
    return {'script': script, 'div': div}

def get_day_usetime_plot(data):
    # Prepare data.
    weekdays = [d.strftime('%A') for d in data]
    hours = [d.strftime('%H:00') for d in data]
    df = pd.DataFrame(list(zip(weekdays, hours)), columns=['Day', 'Time'])
    df['Count'] = 1
    times = df.Time.sort_values(ascending=False).unique().tolist()
    df.replace({'Day': days_en_de_short}, inplace=True)
    df_grouped = df.groupby(['Day', 'Time']).count().reset_index()

    # Create figure.
    TOOLTIPS = """
        <div style="font-size: 0.8rem; color: #00441B">
            <div>
                <span style="font-weight: bold;">Anzahl Videos: </span>
                <span>@Count</span>
            </div>
        </div>
        """

    p = figure(
        x_range=days_de_short,
        y_range=times,
        x_axis_location='above',
        height=500,
        tools='hover,save,pan,box_zoom,reset,wheel_zoom',
        toolbar_location=None,
        tooltips=TOOLTIPS,
        sizing_mode='stretch_width'
    )
    p.border_fill_color = None
    p.outline_line_color = None
    p.grid.grid_line_color = None
    p.xaxis.major_label_text_font_style = 'bold'
    p.axis.axis_line_color = None
    p.axis.axis_label_text_color = '#00441B'
    p.axis.major_tick_line_color = None
    p.axis.major_label_text_font_size = '15px'

    r = p.rect(
        x='Day',
        y='Time',
        source=df_grouped,
        width=1, height=1,
        fill_color=linear_cmap('Count', BuGn9[::-1],
                               low=df_grouped.Count.min(),
                               high=df_grouped.Count.max()),
        line_color=None
    )

    p.add_layout(r.construct_color_bar(
        major_label_text_font_size='10px',
        ticker=BasicTicker(desired_num_ticks=len(BuGn9)),
        formatter=PrintfTickFormatter(format='%d'),
        label_standoff=6,
        border_line_color=None,
        background_fill_color=None,
        padding=5
    ), 'right')

    # Disable touch controls
    p.toolbar.active_drag = None
    p.toolbar.active_scroll = None

    script, div = components(p)
    return {'script': script, 'div': div}
