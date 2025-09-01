import 'package:flutter/material.dart';

class HomeTab {
  final Widget tabBody;
  final String tabTitle;
  final Widget Function(BuildContext context) tabAction;
  final Widget tabIcon;

  const HomeTab({
    required this.tabBody,
    required this.tabTitle,
    required this.tabAction,
    required this.tabIcon,
  });
}
