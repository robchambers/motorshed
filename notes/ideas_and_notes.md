
## Other color maps

Mothers Day:
```
from bokeh.plotting import figure
from bokeh.models import HoverTool, ColumnDataSource

from bokeh.palettes import Magma256,Viridis256,Greys256,Cividis256,Inferno256,Plasma256

from matplotlib.colors import LinearSegmentedColormap
mothers_day = LinearSegmentedColormap.from_list('mothers_day', [
    '#ffffff',
    '#ffdeff', # light pink
    '#ff4af6', # richer pink
#    '#d0c9f5', # light lavender
     '#c384e8', # pink/purple
#     '#eb00ac', # rich pink
#     '#73519c', # purpleish
])
import matplotlib.colors as c
```