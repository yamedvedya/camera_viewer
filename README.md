# General info:
This utility allows displaying images from 2d Tango detectors and to do simple analysis.

Right now TangoTine (LM screens) and Vimba cameras are supported.

Full instruction can be found here: https://confluence.desy.de/display/FSP23/Camera+viewer

Logs are stored in the ~/.petra_camera folder

If you wnat logs to be printed in terminal windows add --log option

# Add new camera:
The camera configuration is stored in the ~/.petra_camera folder

By default the default.xml is loading

If you want to force another config add -p or --profile option with file name

## This is example of minimum entry to add camera:
```xml
<camera name="LM05"
        proxy="TangoTineProxy"
        tango_server="hasep23oh:10000/hasylab/p23_lm5/output"
/>

<camera name="Microscope"
        proxy="VimbaProxy"
        tango_server="hasep23oh:10000/p23/tangovimba/micro"
/>
```

- *proxy* can be 'VimbaProxy" or "TangoTineProxy", "LambdaProxy"  or "DummyProxy"

- *tango_server* is the image source server

- If you want a 12 bit mode of Vimba camera: *high_depth*= 'True'
- If you want a RGB mode of Vimba camera: *color*= 'True'


- In case you have an associated LMAnalysis server you can add it by:
```xml
roi_server = "hasep23oh:10000/p23/lmanalysis/lm5"
```

- In case there is an motor to insert/remove screen it can be specified by:

1. For FSBT motor (you need to have FSBT valve control server running):

```xml
motor_type = 'FSBT'
motor_host = 'hasep23swt01'
motor_port = '12658'
motor_name = 'LM5'
```

2. For Acromag:

```xml
motor_type = 'Acromag' 
valve_tango_server = "p22/acromagxt1121/ch1.02" 
valve_channel="2"
```

- In case of you need to flip/rotate image (in 90 deg terms):

```xml
flip_vertical="True"
flip_horizontal="True"
rotate = '2'
```

### Here is an example of TTGW camera, with associated settings, lmanalysis server, driven by FSBT motor which picture need to be vertically flipped:

```xml
    <camera name="LM05"
            proxy="TangoTineProxy"
            tango_server="hasep23oh:10000/p23/tinecamera/lm5"
            roi_server = "hasep23oh:10000/p23/lmanalysis/lm5"
            widget="CameraSettingsWidget"
            motor_type = 'FSBT'
            motor_host = 'hasep23web'
            motor_port = '12658'
            motor_name = 'LM5'
    />
```

Here is an example of TangoVimba camera, running at 12 bit bw mode, with associated Acromag motor, which picture need to be 90 deg rotated:


```xml
<camera name="Microscope"
        proxy="VimbaProxy"
        tango_server="hasep23oh:10000/p23/tangovimba/micro"
        high_depth="True"
        motor_type = 'Acromag' 
        valve_tango_server = "p23/acromagxt1121/ch1.01" 
        valve_channel="2"
        motor_host = 'hasep23dev'
        rotate = '1'
/>
```