"""General utility functions."""

import argparse
from matplotlib.ticker import AutoMinorLocator
import matplotlib.pyplot as plt
import numpy as np
import xclim


class store_dict(argparse.Action):
    """An argparse action for parsing a command line argument as a dictionary.

    Examples
    --------
    precip=mm/day becomes {'precip': 'mm/day'}
    ensemble=1:5 becomes {'ensemble': slice(1, 5)}
    """

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, dict())
        for value in values:
            key, val = value.split("=")
            if ":" in val:
                start, end = val.split(":")
                try:
                    start = int(start)
                    end = int(end)
                except ValueError:
                    pass
                val = slice(start, end)
            else:
                try:
                    val = int(val)
                except ValueError:
                    pass
            getattr(namespace, self.dest)[key] = val


def convert_units(da, target_units):
    """Convert units.

    Parameters
    ----------
    da : xarray DataArray
        Input array containing a units attribute
    target_units : str
        Units to convert to

    Returns
    -------
    da : xarray DataArray
       Array with converted units
    """

    xclim_unit_check = {
        "deg_k": "degK",
        "kg/m2/s": "kg m-2 s-1",
    }

    if da.attrs["units"] in xclim_unit_check:
        da.attrs["units"] = xclim_unit_check[da.units]

    try:
        da = xclim.units.convert_units_to(da, target_units)
    except Exception as e:
        in_precip_kg = da.attrs["units"] == "kg m-2 s-1"
        out_precip_mm = target_units in ["mm d-1", "mm day-1"]
        if in_precip_kg and out_precip_mm:
            da = da * 86400
            da.attrs["units"] = target_units
        else:
            raise e

    return da


def plot_timeseries_scatter(
    da,
    da_obs=None,
    ax=None,
    title=None,
    label=None,
    obs_label=None,
    units=None,
    time_dim="time",
    outfile=None,
):
    """Timeseries scatter plot of ensemble and observed data.

    Parameters
    ----------
    da : xarray.DataArray
        Stacked ensemble data
    da_obs : xarray.DataArray, optional
        Observed data
    ax : matplotlib.axes.Axes, optional
        Axis to plot on, if None, a new figure is created
    title : str, optional
        Title of the plot
    label : str, optional
        Label for ensemble data
    obs_label : str, optional
        Label for observed data
    units : str, optional
        Units of the data. If None, the units attribute of da is used.
    time_dim : str, optional
        Name of the time dimension in da and da_obs
    outfile : str, optional
        Filename to save the plot

    Returns
    -------
    ax : matplotlib.axes.Axes
        Axis object
    """
    if units is None:
        if "units" in da.attrs:
            units = da.attrs["units"]
        else:
            units = ""

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(10, 4))
    if title is not None:
        ax.set_title(title, loc="left")

    # Plot ensemble data
    ax.scatter(da[time_dim], da, s=3, c="lightskyblue", label=label)
    # Plot observed data
    if da_obs is not None:
        ax.scatter(
            da_obs[time_dim],
            da_obs,
            s=20,
            c="k",
            marker="x",
            label=obs_label,
        )

    ax.set_ylabel(units)
    ax.set_xmargin(1e-2)
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.legend()

    if outfile:
        plt.tight_layout()
        plt.savefig(outfile, dpi=200, bbox_inches="tight")
    return ax


def plot_timeseries_box_plot(
    da,
    da_obs=None,
    ax=None,
    title=None,
    label=None,
    obs_label=None,
    units=None,
    time_dim="time",
    outfile=None,
):
    """Timeseries box and whisker plot of ensemble and observed data.

    Parameters
    ----------
    da : xarray.DataArray
        Stacked ensemble data (see Notes about the time dimension)
    da_obs : xarray.DataArray, optional
        Observed data
    ax : matplotlib.axes.Axes, optional
        Axis to plot on, if None, a new figure is created
    title : str, optional
        Title of the plot
    label : str, optional
        Label for ensemble data
    obs_label : str, optional
        Label for observed data
    units : str, optional
        Units of the data. If None, the units attribute of da is used.
    time_dim : str, optional
        Name of the time dimension in da and da_obs
    outfile : str, optional
        Filename to save the plot

    Returns
    -------
    ax : matplotlib.axes.Axes
        Axis object

    Notes
    -----
    Ensure all time dimensions are set to the correct frequency before calling this function.

    Examples
    --------
    - Input ensemble data grouped by year:
        da = da_orig.copy()
        da.coords["time"] = da.time.dt.year
        da["init_date"] = da.init_date.dt.year
        da = da.stack({"sample": ["ensemble", "init_date", "lead_time"]})
        plot_timeseries_box_plot(da, time_dim="time")
    """
    if units is None:
        if "units" in da.attrs:
            units = da.attrs["units"]
        else:
            units = ""
    # Group model data
    da_grps = [da.isel(sample=v) for k, v in da.groupby(da[time_dim]).groups.items()]

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(10, 4))
    if title is not None:
        ax.set_title(title, loc="left")

    # Plot model box and whiskers for each unique time
    ax.boxplot(da_grps, positions=np.unique(da[time_dim]), manage_ticks=False)

    # Plot observed data as blue crosses
    ax.scatter(da_obs[time_dim], da_obs, s=30, c="b", marker="x", label=obs_label)
    ax.set_ylabel(units)
    ax.set_xmargin(1e-2)
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.legend()

    if outfile:
        plt.tight_layout()
        plt.savefig(outfile, dpi=200, bbox_inches="tight")
    return ax
