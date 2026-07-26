import 'package:flutter/material.dart';

class UnknownPage extends StatelessWidget {
  const UnknownPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Return to Previous Page')),
      body: Center(
        child: Text(
          'This Page is unavailable',
          style: const TextStyle(fontSize: 24),
        ),
      ),
    );
  }
}
