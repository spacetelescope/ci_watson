"""Functions for interpreting resource_tracker outputs."""

from collections import defaultdict
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
    test_date : str
        Date the test was run.

    failures : int
        Number of test failures in the run.

    peakmem_dict : dict
        Dictionary mapping a test to another dictionary
        containing its benchmark statistics, e.g.::

            {
                (classname, name): {
                    "peakmem": 0.1,
                    "time": 10
                }
            }

    Raises
    ------
    ValueError
        Unexpected XML layout.
    """

    # Create the Element Tree object from the XML file and get the top level root.
    tree = ET.parse(source)
    root = tree.getroot()

    # Save all the info into the following dictionary.
    peakmem_dict = defaultdict(dict)

    # The first element is called testsuites, this only contains one testsuite, which
    # has the datetime in which the tests were ran, variable called timestamp, in UT.
    test_date = None
    for element in root.iter("testsuites"):
        items = element.findall("testsuite")[0]
        if items is not None:
            test_date = items.attrib["timestamp"]
            # Also get the failures variable.
            failures = int(items.attrib["failures"])

            break
        else:
            raise ValueError("XML format change!")

    if test_date is None:
        raise ValueError("No test date found in XML file.")

    # All test cases will be under the testsuite element, as follows:
    #
    # <testcase classname="pkg.module" name="test_name" time="16.539">
    #   <properties>
    #     <property name="tracked-peakmem" value="802075618"/>
    #     <property name="tracked-time" value="16.49477450037375"/>
    #   </properties>
    # </testcase>
    #
    for element in root.iter("testcase"):
        tracked_mem_elements = element.findall("properties/property")

        # If this list does not exist, no memory peak was recorded.
        if tracked_mem_elements:
            # Some tests have the same name but are in different modules,
            # so we need tuple as unique key.
            # Also make sure the test name does not contain / because this
            # causes problems with pathlib later.
            classname = element.attrib["classname"]
            testname = element.attrib["name"].replace("/", "--")
            key = (classname, testname)

            for prop in tracked_mem_elements:
                # Save the peak memory (bytes) and run time (seconds).
                for attrname in ("peakmem", "time"):
                    if prop.attrib["name"] == f"tracked-{attrname}":
                        peakmem_dict[key][attrname] = prop.get("value")

    return test_date, failures, peakmem_dict
