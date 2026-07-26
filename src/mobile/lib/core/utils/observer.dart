import 'package:flutter_bloc/flutter_bloc.dart';
// import 'dart:convert'; // No longer needed for the custom printer

class CoreObserver extends BlocObserver {
  void _printHeader(String type, BlocBase bloc) {
    // Using print for console output as is typical in Dart command-line/Flutter debug scenarios
    // ignore: avoid_print
    print('\n========== $type: ${bloc.runtimeType} ==========');
  }

  @override
  void onCreate(BlocBase bloc) {
    super.onCreate(bloc);
    _printHeader('Create', bloc);
    // ignore: avoid_print
    print('Initial State:'); // Header for state
    _safePrint(bloc.state);
  }

  @override
  void onEvent(Bloc bloc, Object? event) {
    super.onEvent(bloc, event);
    _printHeader('Event', bloc);
    _safePrint(event);
  }

  @override
  void onChange(BlocBase bloc, Change change) {
    super.onChange(bloc, change);
    _printHeader('Change', bloc);
    _safePrint(change);
  }

  @override
  void onTransition(Bloc bloc, Transition transition) {
    super.onTransition(bloc, transition);
    _printHeader('Transition', bloc);
    _safePrint(transition);
  }

  @override
  void onError(BlocBase bloc, Object error, StackTrace stackTrace) {
    super.onError(bloc, error, stackTrace);
    _printHeader('Error', bloc);
    // ignore: avoid_print
    print('Error: $error\nStackTrace:\n$stackTrace');
  }

  String _truncate(String text, int maxLength) {
    if (text.length <= maxLength) {
      return text;
    }
    // Ensure maxLength is not too small for ellipsis
    if (maxLength < 3) {
      if (maxLength <= 0) return ""; // Handle non-positive maxLength
      return text.substring(0, maxLength); // Not enough space for "..."
    }
    return text.substring(0, maxLength - 3) + '...';
  }

  void _buildFormattedStringLines(
    Object? data,
    String currentIndent,
    List<String> lines,
  ) {
    const String indentStep = '  '; // 2 spaces for each nesting level
    const int maxLength = 80; // Maximum characters for a field/line part

    Object? processedData = data;

    // Attempt to use toJson() for objects that are not already basic types or collections
    if (data != null &&
        !(data is Map) &&
        !(data is List) &&
        !(data is String) &&
        !(data is num) &&
        !(data is bool)) {
      try {
        // Dynamically invoke toJson() if it exists
        processedData = (data as dynamic).toJson();
      } catch (_) {
        // If toJson() fails or doesn't exist, processedData remains the original data.
        // It will be handled by toString() in the fallback case.
      }
    }

    if (processedData == null) {
      lines.add('$currentIndent${_truncate('null', maxLength)}');
    } else if (processedData is String) {
      // Handle multi-line strings: indent and truncate each line
      final stringLines = processedData.split('\n');
      for (final linePart in stringLines) {
        lines.add('$currentIndent${_truncate(linePart, maxLength)}');
      }
    } else if (processedData is num || processedData is bool) {
      lines.add(
        '$currentIndent${_truncate(processedData.toString(), maxLength)}',
      );
    } else if (processedData is List) {
      if (processedData.isEmpty) {
        lines.add('$currentIndent[]');
      } else {
        lines.add('$currentIndent[');
        final newIndent = currentIndent + indentStep;
        for (int i = 0; i < processedData.length; i++) {
          // Display list index as a "field"
          lines.add('$newIndent${_truncate("[$i]:", maxLength)}');
          // Recursively print the item, indented further
          _buildFormattedStringLines(
            processedData[i],
            newIndent + indentStep,
            lines,
          );
        }
        lines.add('$currentIndent]');
      }
    } else if (processedData is Map) {
      if (processedData.isEmpty) {
        lines.add('$currentIndent{}');
      } else {
        lines.add('$currentIndent{');
        final newIndent = currentIndent + indentStep;
        processedData.forEach((key, value) {
          // Display map key as a "field"
          lines.add('$newIndent${_truncate(key.toString(), maxLength)}:');
          // Recursively print the value, indented further
          _buildFormattedStringLines(value, newIndent + indentStep, lines);
        });
        lines.add('$currentIndent}');
      }
    } else {
      // Fallback for other complex objects (after toJson attempt)
      // Convert to string, handle multi-line, indent, and truncate
      final stringRepresentation = processedData.toString();
      final stringLines = stringRepresentation.split('\n');
      for (final linePart in stringLines) {
        lines.add('$currentIndent${_truncate(linePart, maxLength)}');
      }
    }
  }

  void _safePrint(Object? data) {
    final lines = <String>[];
    _buildFormattedStringLines(data, '', lines); // Start with no indent
    for (final line in lines) {
      // ignore: avoid_print
      print(line); // Each string in 'lines' is a pre-formatted line
    }
  }
}
