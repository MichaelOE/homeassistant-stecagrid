# Stecagrid
Home Assistant custom integration for reading information from Steca StecaGrid inverters with proprietary RS485 protocol (like ex. the StecaGrid 8000+ 3ph)

[![BuyMeCoffee][buymecoffeebadge]][michaeloe-buymecoffee]

## Target
The project is meant to get current power production from a StecaGrid 8000+ 3ph solar inverter

## Method
I used a cheap LAN-to-RS485 converter to connect to the inverter - https://raspberrypi.dk/produkt/rs485-til-ethernet-converter-til-eu/

## Sensors
Several sensors from the inverter is exposed, including:
- Current ouptut power to grid
- Current panel power
- Current panel voltage
- Current panel current
- Todays total output
 
![billede](https://github.com/user-attachments/assets/3ae54f9b-27df-4349-b650-ae6786a030f6)

## Credits
The physical connection I got information from here: https://svgroeneveld.blogspot.com/2015/08/communication-with-inverter.html

I got inspiration from this Arduino project: https://github.com/tsybolek/Aquarea_Stecagrid_Modbus_NodeMCU/blob/master/aquarea_steca_modbus_public.ino

[buymecoffeebadge]: https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png
[michaeloe-buymecoffee]: https://buymeacoffee.com/michaeloe
