import 'package:flutter/material.dart';

ThemeData getCoreTheme({
  required Color seedColor,
  required Brightness brightness,
}) {
  // Create the ColorScheme first
  final ColorScheme colorScheme = ColorScheme.fromSeed(
    seedColor: seedColor,
    brightness: brightness,
  );
  // Return ThemeData with the colorScheme
  return ThemeData(colorScheme: colorScheme, useMaterial3: true);
}

// Use the function to create the light theme
final ThemeData lightTheme = getCoreTheme(
  seedColor: Colors.red,
  brightness: Brightness.light,
).copyWith();
// Use the function to create the dark theme
final ThemeData darkTheme = getCoreTheme(
  seedColor: Colors.red,
  brightness: Brightness.dark,
);
