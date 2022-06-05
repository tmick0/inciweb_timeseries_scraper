from inciweb_timeseries_scraper import get_all_data
import argparse
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import csv
import sys


parser = argparse.ArgumentParser()
parser.add_argument("mode", type=lambda s: s.lower(), help="operation mode: plot or csv")
parser.add_argument("incident_number", type=int, help="incident number from the URL on InciWeb")
parser.add_argument("--output", "-o", help="output destination for csv or plot (default stdout or interactive)", default=None)

args = parser.parse_args()

if not args.mode in ["plot", "csv"]:
    raise ValueError(f"invalid mode {args.mode}")

name, data = get_all_data(args.incident_number)

if args.mode == "csv":
    output = sys.stdout
    if args.output is not None:
        output = open(args.output, 'w')
    
    writer = csv.writer(output)
    for row in sorted(data, key=lambda r: r[0]):
        writer.writerow(row)
        
elif args.mode == "plot":
    dates, areas, containments = zip(*data)

    fig, ax0 = plt.subplots()
    ax0.set_title(name)
    ax0.set_xlabel("Date")
    ax1 = ax0.twinx()
    ax0.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%Y'))
    ax0.xaxis.set_major_locator(mdates.DayLocator())

    line0, = ax0.plot(dates, areas, c='r')
    line0.set_label("Area")
    ax0.set_ylabel("Area (acres)")

    line1, = ax1.plot(dates, containments, c='b')
    line1.set_label("Containment")
    ax1.set_ylabel("Containment (%)")

    lines = [line0, line1]
    ax0.legend(lines, [l.get_label() for l in lines])
    fig.autofmt_xdate()

    if args.output is None:
        plt.show()
    else:
        fig.savefig(args.output)
