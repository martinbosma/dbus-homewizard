## DISCLAIMER
This is a personal project, far from finished and not officially supported by Victron Energy.\
The project is outdated and has not been maintained for quite some time.

# dbus-homewizard

This application reads data from a HomeWizard energy monitor and turns it into a grid meter service on dbus. 
This allows VenusOS to use your HomeWizard energy meter as a grid meter.

## Limitations

Currently only the HomeWizard Wi-Fi P1 meter is supported.
The update rate of the smart meter depends on the version of the smart meter.
With a SMR 5.0 meter the update rate is every second for the power readings.
Smart meters with a version lower than SMR 5.0 have an update rate of 10s and
are therefore not suitable for usage in control loops.
