import 'package:flutter/material.dart';

import 'cosmic_background.dart';

class KhotwaScaffold extends StatelessWidget {
  final Widget child;
  final String? title;
  final List<Widget>? actions;

  const KhotwaScaffold({super.key, required this.child, this.title, this.actions});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: title == null
          ? null
          : AppBar(
              title: Text(title!),
              centerTitle: true,
              backgroundColor: Colors.transparent,
              elevation: 0,
              actions: actions,
            ),
      body: SafeArea(
        child: CosmicBackground(
          child: Padding(padding: const EdgeInsets.all(16), child: child),
        ),
      ),
    );
  }
}
