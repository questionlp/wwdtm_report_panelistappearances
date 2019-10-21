# -*- coding: utf-8 -*-
# Copyright (c) 2018-2019 Linh Pham
# wwdtm_panelistvspanelist is relased under the terms of the Apache License 2.0
"""WWDTM Panelist Appearance Report Generator"""

import argparse
from collections import OrderedDict
from datetime import datetime
import json
import os
from typing import List, Dict, Text
import mysql.connector
import pytz

from jinja2 import Environment, FileSystemLoader

def retrieve_panelist_appearance_counts(panelist_id: int,
                                        database_connection: mysql.connector.connect
                                       ) -> List[Dict]:
    """Retrieve yearly apperance count for the requested panelist ID"""

    cursor = database_connection.cursor()
    query = ("SELECT YEAR(s.showdate) AS year, COUNT(p.panelist) AS count "
             "FROM ww_showpnlmap pm "
             "JOIN ww_shows s ON s.showid = pm.showid "
             "JOIN ww_panelists p ON p.panelistid = pm.panelistid "
             "WHERE pm.panelistid = %s AND s.bestof = 0 "
             "AND s.repeatshowid IS NULL "
             "GROUP BY p.panelist, YEAR(s.showdate) "
             "ORDER BY p.panelist ASC, YEAR(s.showdate) ASC")
    cursor.execute(query, (panelist_id, ))
    result = cursor.fetchall()

    if not result:
        return None

    appearances = OrderedDict()
    total_appearances = 0
    for row in result:
        appearances[row[0]] = row[1]
        total_appearances += row[1]

    appearances["total"] = total_appearances
    return appearances

def retrieve_all_panelist_appearance_counts(database_connection: mysql.connector.connect
                                           ) -> List[Dict]:
    """Retrieve all appearance counts for all panelists from the
    database"""

    cursor = database_connection.cursor()
    query = ("SELECT DISTINCT p.panelistid, p.panelist "
             "FROM ww_showpnlmap pm "
             "JOIN ww_panelists p ON p.panelistid = pm.panelistid "
             "JOIN ww_shows s ON s.showid = pm.showid "
             "WHERE s.bestof = 0 AND s.repeatshowid IS NULL "
             "ORDER BY p.panelist ASC")
    cursor.execute(query)
    result = cursor.fetchall()

    if not result:
        return None

    panelists = []
    for row in result:
        panelist = {}
        panelist_id = row[0]
        panelist["name"] = row[1]
        appearances = retrieve_panelist_appearance_counts(panelist_id,
                                                          database_connection)
        panelist["appearances"] = appearances
        panelists.append(panelist)

    return panelists

def retrieve_all_years(database_connection: mysql.connector.connect) -> List[int]:
    """Retrieve a list of all available show years"""
    cursor = database_connection.cursor()
    query = ("SELECT DISTINCT YEAR(s.showdate) FROM ww_shows s "
             "ORDER BY YEAR(s.showdate) ASC")
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()

    if not result:
        return None

    years = []
    for row in result:
        years.append(row[0])

    return years

def load_config():
    """Load configuration values from configuration file and from
    options passed into script execution"""

    # Read in configuration file
    with open("config.json", "r") as config_file:
        config_dict = json.load(config_file)

    # Read in options passed in
    parser = argparse.ArgumentParser()
    parser.add_argument("--ga-property-code",
                        dest="ga_property_code",
                        help="Google Analytics Property Code (overrides config.json)")
    args = parser.parse_args()

    if (not config_dict["google_analytics_property_code"]
            and args.ga_property_code):
        config_dict["google_analytics_property_code"] = args.ga_property_code

    return config_dict

def render_report(show_years: List[int],
                  panelists: List[Dict],
                  ga_property_code: Text) -> Text:
    """Render appearances report using Jinja2"""

    # Setup Jinja2 Template
    template_loader = FileSystemLoader("./template")
    template_env = Environment(loader=template_loader,
                               trim_blocks=True,
                               lstrip_blocks=True)
    template_file = "report.tmpl.html"
    template = template_env.get_template(template_file)

    # Generate timestamp to include in page footer
    time_zone = pytz.timezone("America/Los_Angeles")
    rendered_date_time = datetime.now(time_zone)

    # Build dictionary to pass into template renderer
    render_data = {}
    render_data["show_years"] = show_years
    render_data["panelists"] = panelists
    render_data["ga_property_code"] = ga_property_code
    render_data["rendered_at"] = rendered_date_time.strftime("%A, %B %d, %Y %H:%M:%S %Z")

    # Render the report and write out to output directory
    report = template.render(render_data=render_data)
    return report

def main():
    """Bootstrap database connection, retrieve panelist appearance data,
    generate the report and create an output bundle"""

    app_config = load_config()
    database_connection = mysql.connector.connect(**app_config["database"])
    panelists = retrieve_all_panelist_appearance_counts(database_connection)
    show_years = retrieve_all_years(database_connection)

    rendered_report = render_report(show_years,
                                    panelists,
                                    app_config["google_analytics_property_code"])
    print(rendered_report)

# Only run if executed as a script and not imported
if __name__ == '__main__':
    main()
