import 'package:flutter/material.dart';

class ThemeController {
  ThemeController._();

  static final ThemeController instance = ThemeController._();

  final ValueNotifier<ThemeMode> mode = ValueNotifier<ThemeMode>(ThemeMode.light);

  void toggle() {
    mode.value = mode.value == ThemeMode.light ? ThemeMode.dark : ThemeMode.light;
  }
}
