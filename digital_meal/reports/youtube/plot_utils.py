import math
import pandas as pd

from bokeh.embed import components
from bokeh.plotting import figure

from digital_meal.website.constants import COLORS


def get_channel_plot(channel_list, n_channels=10):
    channels = pd.Series(channel_list)
    x_labels = channels.value_counts().keys().to_list()
    y_values = channels.value_counts().values.tolist()

    # Create barplot with X most watched channels
    p = figure(
        x_range=x_labels[:n_channels],
        height=600, width=1000,
        toolbar_location=None,
        tools=''
    )
    p.vbar(
        x=x_labels[:n_channels],
        top=y_values[:n_channels],
        width=0.1,
        line_color=None,
        fill_color=COLORS['PURPLE_DARKEST']
    )
    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    p.yaxis.axis_label = 'Anzahl Videos'
    p.yaxis.axis_label_text_font_size = '20px'
    p.yaxis.axis_label_text_font_style = 'normal'
    p.border_fill_color = None
    p.outline_line_color = None
    p.background_fill_color = None
    p.scatter(
        x_labels,
        y_values,
        marker='circle',
        size=12,
        fill_color=COLORS['LIGHTGREEN_DARKER'],
        line_color=None
    )
    p.yaxis.minor_tick_line_color = None
    p.axis.major_tick_line_color = None
    p.xaxis.major_label_orientation = math.pi/3
    p.xaxis.axis_line_color = COLORS['PURPLE_DARKER']
    p.ygrid.grid_line_color = COLORS['PURPLE']
    p.yaxis.axis_line_color = None
    p.yaxis.axis_label_text_color = 'black'
    p.xaxis.major_label_text_font_size = '15px'
    p.axis.major_label_text_color = 'black'

    script, div = components(p)
    return {'script': script, 'div': div}


def get_subscription_plot(channel_list, n_channels=10):
    channels = pd.Series(channel_list)
    x_labels = channels.value_counts().keys().to_list()
    y_values = channels.value_counts().values.tolist()

    # Create barplot with X most watched channels
    p = figure(
        x_range=x_labels[:n_channels],
        height=600, width=1000,
        toolbar_location=None,
        tools=''
    )
    p.vbar(
        x=x_labels[:n_channels],
        top=y_values[:n_channels],
        width=0.1,
        line_color=None,
        fill_color=COLORS['PURPLE_DARKEST']
    )
    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    p.yaxis.axis_label = 'Anzahl Abos'
    p.yaxis.axis_label_text_font_size = '20px'
    p.yaxis.axis_label_text_font_style = 'normal'
    p.border_fill_color = None
    p.outline_line_color = None
    p.background_fill_color = None
    p.scatter(
        x_labels,
        y_values,
        marker='circle',
        size=12,
        fill_color=COLORS['LIGHTGREEN_DARKER'],
        line_color=None
    )
    p.yaxis.minor_tick_line_color = None
    p.axis.major_tick_line_color = None
    p.xaxis.major_label_orientation = math.pi/3
    p.xaxis.axis_line_color = COLORS['PURPLE_DARKER']
    p.ygrid.grid_line_color = COLORS['PURPLE']
    p.yaxis.axis_line_color = None
    p.yaxis.axis_label_text_color = 'black'
    p.xaxis.major_label_text_font_size = '15px'
    p.axis.major_label_text_color = 'black'

    script, div = components(p)
    return {'script': script, 'div': div}
