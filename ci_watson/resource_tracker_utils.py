"""Functions for interpreting resource_tracker outputs."""

from datetime import datetime
from xml.etree import ElementTree as ET

__all__ = ["parse_single_junit_result_xml"]


def parse_single_junit_result_xml(source):
    """
    Parse a single junit result XML output.

    Parameters
    ----------
    source : str or fileobj
        Filename or file object containing XML data.

    Returns
    -------
    test_date : date
        Date the test was run.

    failures : int
        Number of test failures in the run.

    peakmem_dict : dict
        Dictionary mapping modified test name to another
        dictionary containing "peakmem" and "time"
        benchmark statistics.

    Raises
    ------
    ValueError
        Unexpected XML layout.
    """

    # Create the Element Tree object from the XML file and get the top level, root
    tree = ET.parse(source)
    root = tree.getroot()

    # Save all the info into the following dictionary and use a specific datetime format
    peakmem_dict = {}
    date_format = "%Y-%m-%dT%H:%M:%S.%f%z"

    # The first element is called testsuites, this only contains one testsuite, which
    # has the datetime in which the tests were ran, variable called timestamp, in UT.
    failures = 0
    test_date = None
    for element in root.iter("testsuites"):
        items = element.findall("testsuite")[0]
        if items is not None:
            test_date = datetime.strptime(items.attrib["timestamp"], date_format)
            # Also get the failures variable
            failures = int(items.attrib["failures"])

            break
        else:
            raise ValueError("XML format change!")

    # Sanity check
    if test_date is None:
        raise ValueError("No test date found in XML file.")

    # All test cases will be under the testsuite element.
    for element in root.iter("testcase"):
        # For this element, the peak memory is under properties/property
        tracked_mem_elements = element.findall("properties/property")

        # If this list does not exist, no memory peak was recorded
        if tracked_mem_elements:
            # some tests have the same name but are run for different modes
            # get the class and store it
            classname = element.attrib["classname"]
            # add the instrument mode to the test name from the class
            inst_mode = classname.split(sep="test_")[-1]
            # get the test name and make it unique
            test_name = element.attrib["name"] + "_M_" + inst_mode
            # make sure the test name does not contain / because this
            # causes problems with pathlib
            if "/" in test_name:
                test_name = test_name.replace("/", "--")
            peakmem_dict[test_name] = {}
            peakmem_dict[test_name]["classname"] = classname
            for prop in tracked_mem_elements:
                # save the peak memory and running time
                if prop.attrib["name"] == "tracked-peakmem":
                    peakmem_dict[test_name]["peakmem"] = prop.get("value")
                elif prop.attrib["name"] == "tracked-time":
                    peakmem_dict[test_name]["time"] = prop.get("value")

    return test_date, failures, peakmem_dict
