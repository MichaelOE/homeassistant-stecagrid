# Stecagrid
Home Assistant custom integration for reading information from Steca StecaGrid inverters with proprietary RS485 protocol (like ex. the StecaGrid 8000+ 3ph)

[![BuyMeCoffee][buymecoffeebadge]][michaeloe-buymecoffee]

## Target
The project is meant to get current power production from a StecaGrid 8000+ 3ph solar inverter

## Method
I used a cheap LAN-to-RS485 converter so connect to the inverter https://raspberrypi.dk/produkt/rs485-til-ethernet-converter-til-eu/

## Sensors
Currently I have the interver return only 2 values - current output power and the inverter timestamp.
According to the Steca docs, it should return other values as well, but maybe my inverter firmware is too old as it just returns 'not supported' for other queries.

![billede](https://github.com/user-attachments/assets/c2e4b919-ea91-4371-859f-10ad60c8dd92)


## Credits
The physical connection I got information from here: https://svgroeneveld.blogspot.com/2015/08/communication-with-inverter.html

I got inspiration from this Arduino project: https://github.com/tsybolek/Aquarea_Stecagrid_Modbus_NodeMCU/blob/master/aquarea_steca_modbus_public.ino

[buymecoffeebadge]: https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png
[michaeloe-buymecoffee]: https://buymeacoffee.com/michaeloe
