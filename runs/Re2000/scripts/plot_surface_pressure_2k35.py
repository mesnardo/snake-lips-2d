"""Plot the profile of the surface pressure."""

import pathlib

import numpy
import pandas
from matplotlib import pyplot
from scipy.interpolate import RegularGridInterpolator

import petibmpy


def get_surface_pressure(simudir):
    # Set data directory.
    datadir = simudir / 'output'

    # Load boundary coordinates from file.
    filepath = simudir / 'snake.body'
    xb, yb = petibmpy.read_body(filepath, skiprows=1)

    # Compute mid-points on the boundary.
    xb_m, yb_m = 0.5 * (xb[:-1] + xb[1:]), 0.5 * (yb[:-1] + yb[1:])

    # Compute the surface normals.
    x_n, y_n = (yb[1:] - yb[:-1]), -(xb[1:] - xb[:-1])
    norms = numpy.array([numpy.linalg.norm([xi, yi])
                         for xi, yi in zip(x_n, y_n)])
    x_n /= norms
    y_n /= norms

    # List of time values to process.
    times = numpy.arange(50.0, 80.0 + 1, 2.0)

    # Define the grid interpolator.
    filepath = datadir / 'probe-p.h5'
    grid, p = petibmpy.ProbeVolume('p', 'p').read_hdf5(filepath, times[0])
    interpolator = RegularGridInterpolator(grid, p.T)

    # Define the interpolation points.
    dist = 0.01  # distance to immersed boundary
    x_interp, y_interp = xb_m + dist * x_n, yb_m + dist * y_n
    points = numpy.array([x_interp, y_interp]).T

    # Interpolate the pressure at interpolation points (averaged over time).
    p_interp = numpy.zeros_like(x_interp)
    for time in times:
        _, p = petibmpy.ProbeVolume('p', 'p').read_hdf5(filepath, time)
        interpolator.values = p.T
        p_interp += interpolator(points)
    p_interp /= len(times)

    return xb_m, p_interp


def get_le_pressure(x, p):
    mask = numpy.where(abs(x - min(x)) < 0.05)[0]
    x, p = x[mask], p[mask]
    idx = numpy.argmin(p)
    return x[idx], p[idx]


# Set directories.
maindir = pathlib.Path(__file__).absolute().parents[1]
folders = ['both_lips/2k35', 'front_lip/2k35', 'back_lip/2k35', 'no_lips/2k35']
labels = ['Both', 'Front', 'Back', 'None']

df = pandas.DataFrame(columns=['Case', 'x_LE', 'p_LE'])

data = dict()
for folder, label in zip(folders, labels):
    data[label] = get_surface_pressure(maindir / folder)
    df.loc[len(df)] = [label, *get_le_pressure(*data[label])]

# Load surface pressure from Krishnan et al. (2014).
filepath = maindir / 'data' / 'krishnan_et_al_2014_surface_pressure_2k35.txt'
with open(filepath, 'r') as infile:
    pk, xk, yk = numpy.loadtxt(infile, usecols=(0, 2, 3), unpack=True)
# Displace x-coordinates to align with us.
x, _ = data[labels[0]]
xk += abs(xk.min()) - abs(x.min())
df.loc[len(df)] = ['Krishnan et al. (2014)', *get_le_pressure(xk, pk)]

print(df.set_index('Case').round(decimals=2))

# Plot the surface pressure.
pyplot.rc('font', family='serif', size=14)
fig, ax = pyplot.subplots(figsize=(6.0, 4.0))
ax.set_xlabel('x-coordinate')
ax.set_ylabel('Surface pressure')
for label, (x, p) in data.items():
    ax.plot(x, p, label=label)
ax.plot(xk, pk, color='black', linestyle='--',
        label='Krishnan et al. (2014)')
ax.legend(frameon=False, ncol=2, prop=dict(size=10))
ax.axis((-0.6, 0.6, -2.0, 1.0))
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
fig.tight_layout()

# Save the Matplotlib figure as PNG.
figdir = maindir / 'figures'
figdir.mkdir(parents=True, exist_ok=True)
filepath = figdir / 'surface_pressure_2k35.png'
fig.savefig(filepath, dpi=300, bbox_inches='tight')

pyplot.show()
