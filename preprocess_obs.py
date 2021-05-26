"""Process observational data into forecast (i.e. initial date / lead time) format."""

import sys
repo_dir = sys.path[0]
import pdb
import argparse
import re

import git
import numpy as np
import xarray as xr
import cmdline_provenance as cmdprov

import myfuncs


def stack_by_init_date(da, init_dates, n_lead_steps, freq='D'):
    """Stack timeseries array in inital date / lead time format.

    Args:
      da (xarray DataArray)
      init_dates (numpy ndarray) : Initial dates in datetime64[ns] format
      n_lead_steps (int) : Maximum lead time
      freq (str) : Time-step frequency
    """
    
    rounded_times = da['time'].dt.floor(freq).values
    ref_time = np.datetime_as_string(init_dates[0], unit='D')
    ref_array = da.sel(time=ref_time).values    

    time2d = np.empty((len(init_dates), n_lead_steps), 'datetime64[ns]')
    init_date_indexes = []
    offset = n_lead_steps - 1
    for ndate, date in enumerate(init_dates):
        start_index = np.where(rounded_times == date)[0][0]
        end_index = start_index + n_lead_steps
        time2d[ndate, :] = da['time'][start_index:end_index].values
        init_date_indexes.append(start_index + offset)

    da = da.rolling(time=n_lead_steps, min_periods=1).construct("lead_time")
    da = da.assign_coords({'lead_time': da['lead_time'].values})
    da = da.rename({'time': 'init_date'})
    da = da[init_date_indexes, ::]
    da = da.assign_coords({'init_date': time2d[:, 0]})
    da = da.assign_coords({'time': (['init_date', 'lead_time'], time2d)})
    da['lead_time'].attrs['units'] = freq

    actual_array = da.sel({'init_date': ref_time, 'lead_time': 0}).values
    np.testing.assert_allclose(actual_array, ref_array)
    
    # TODO: Return nans if requested times lie outside of the available range
    
    return da


def check_dates(date_list):
    """Check for YYYY-MM-DD format."""

    date_pattern = '([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})'
    for date in date_list:
        assert re.search(date_pattern, date), \
            'Date format must be YYYY-MM-DD'


def _main(args):
    """Run the command line program."""

    da = myfuncs.open_file(args.infile, args.invar,
                           outvar=args.outvar,
                           dataset=args.dataset,
                           no_leap_days=args.no_leap_days,
                           region=args.region,
                           units=args.units)
            
    check_dates(args.init_dates)
    init_dates = np.array(args.init_dates, dtype='datetime64[ns]')
    da = stack_by_init_date(da, init_dates, args.n_lead_steps)

    ds = da.to_dataset()
    repo = git.Repo(repo_dir)
    repo_url = repo.remotes[0].url.split('.git')[0]
    new_log = cmdprov.new_log(code_url=repo_url)
    ds.attrs['history'] = new_log

    ds = ds.chunk({'init_date': -1, 'lead_time': -1})
    ds.to_zarr(args.outfile, mode='w')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
                                     
    parser.add_argument("infile", type=str, help="Input file")
    parser.add_argument("invar", type=str, help="Input variable name")
    parser.add_argument("outvar", type=str, help="Output variable name")
    parser.add_argument("outfile", type=str, help="Output file")
    
    parser.add_argument("--n_lead_steps", type=int, required=True,
                        help="Number of lead time steps")
    parser.add_argument("--init_dates", type=str, nargs='*', required=True,
                        help="Initial dates (YYYY-MM-DD format)")
    parser.add_argument("--dataset", type=str, choices=('JRA-55', 'AWAP'),
                        help="Dataset name for custom metadata handling")
    parser.add_argument("--region", type=str, choices=myfuncs.regions.keys(),
                        help="Select spatial region from data")
    parser.add_argument("--no_leap_days", action="store_true", default=False,
                        help="Remove leap days from time series [default=False]")
    parser.add_argument("--units", type=str, default=None,
                        help="Convert to these units")

    args = parser.parse_args()
    _main(args)
