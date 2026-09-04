# wokwi-potentiometer Reference | Wokwi Docs

> Source: https://docs.wokwi.com/parts/wokwi-potentiometer
> Cached: 2026-09-03T18:33:24.306Z

---

- [](/)
- Diagram Reference
- wokwi-potentiometer

On this page# wokwi-potentiometer Reference

Knob-controlled variable resistor (linear potentiometer)

The information below also applies to the [slide potentiometer](/parts/wokwi-slide-potentiometer).

## Pin names[​](#pin-names)

NameDescriptionGNDGroundSIGOutput, connect to an analog input pinVCCSupply voltage
Note: Wokwi does **not** support full analog simulation, so you will get the same
results even if you don&#x27;t connect the GND/VCC pins.
This may change in the future, so it&#x27;s a good idea to connect GND/VCC anyway.

## Attributes[​](#attributes)

NameDescriptionDefault valuevalueInitial value of the potentiometer, between 0 and 1023"0"
## Using the Potentiometer in Arduino[​](#using-the-potentiometer-in-arduino)

Connect the SIG pin to one of Arduino&#x27;s analog input pins (A0, A1, …). Then use the `analogRead()` function to read the current value of the potentiometer.

The following code example assumes that the potentiometer is connected to A0.
It will read and print the current value of the potentiometer every 100 milliseconds:
```
void setup() {
  Serial.begin(115200);
  pinMode(A0, INPUT);
}

void loop() {
  int value = analogRead(A0);
  Serial.println(value);
  delay(100);
}

```

You can [run the example on Wokwi](https://wokwi.com/projects/298685457758159369). Observe how the plotter graph changes as you move the potentiometer&#x27;s knob.

## Keyboard control[​](#keyboard-control)

You can control the potentiometer with the keyboard:

- Left / Right - fine movement

- Page Up / Page Down - coarse movement

- Home / End - move to the start (0) or the end (1023) of the range

You&#x27;ll need to click on the potentiometer before using these keyboard shortcuts.

## Automation controls[​](#automation-controls)

The potentiometer can be controlled using [Automation Scenarios](/wokwi-ci/automation-scenarios). It exposes the following controls:

ControlTypeDescriptionpositionfloatMoves the potentiometer to the given position, between 0.0 and 1.0
The following example set the potentiometer to the middle position:

```
  - set-control:
      part-id: pot1
      control: position
      value: 0.5

```

## Simulator examples[​](#simulator-examples)

- [Knob](https://wokwi.com/projects/344892191015961170) - Control a [servo](/parts/wokwi-servo) with a potentiometer

- [Plot](https://wokwi.com/projects/298685457758159369) - Plot potentiometer values in the Serial Plotter

- [Block shooter](https://wokwi.com/projects/291960996581343753) - Breakout style game

[Edit this page](https://github.com/wokwi/wokwi-docs/edit/main/docs/parts/wokwi-potentiometer.md)