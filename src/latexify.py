#Original Author: Prof. Nipun Batra
# nipunbatra.github.io
#Author who this was taken from
# angeris.github.io

from math import sqrt 
import matplotlib

SPINE_COLOR = 'gray'

def latexify(fig_width=None, fig_height=None, font_size=12, columns=2):
    """Set up matplotlib's RC params for LaTeX plotting.
    Call this before plotting a figure.
    Parameters
    ----------
    fig_width : float, optional, inches
    fig_height : float,  optional, inches
    columns : {1, 2}
    """

    # code adapted from https://scipy.github.io/old-wiki/pages/Cookbook/Matplotlib/LaTeX_Examples.html

    # Width and max height in inches for IEEE journals taken from
    # computer.org/cms/Computer.org/Journal%20templates/transactions_art_guide.pdf

    assert(columns in [1,2])

    x1 = 3.39
    x2 = 6.9
    if fig_width is None:
        fig_width = x1 if columns==1 else x2 # width in inches

    if fig_height is None:
        golden_mean = (sqrt(5)-1.0)/2.0    # Aesthetic ratio
        fig_height = fig_width*golden_mean # height in inches

    MAX_HEIGHT_INCHES = 8.0
    if fig_height > MAX_HEIGHT_INCHES:
        print("WARNING: fig_height too large:" + fig_height + 
              "so will reduce to" + MAX_HEIGHT_INCHES + "inches.")
        fig_height = MAX_HEIGHT_INCHES

    # NB (bart): default font-size in latex is 11. This should exactly match 
    # the font size in the text if the figwidth is set appropriately.
    # Note that this does not hold if you put two figures next to each other using
    # minipage. You need to use subplots.
    params = {#'backend': 'ps',
              'text.latex.preamble': ['\\usepackage{gensymb}'],
              'axes.labelsize': font_size, # fontsize for x and y labels (was 12 and before 10)
              'axes.titlesize': font_size,
              'font.size': font_size, # was 12 and before 10
              'legend.fontsize': font_size, # was 12 and before 10
              'xtick.labelsize': font_size,
              'ytick.labelsize': font_size,
              'text.usetex': True,
              'figure.figsize': [fig_width,fig_height],
              'figure.dpi': 140,
              'font.family': 'serif'
    }

    matplotlib.rcParams.update(params)
    return