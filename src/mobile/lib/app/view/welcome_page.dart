import 'package:flutter/material.dart';
import 'package:animated_text_kit/animated_text_kit.dart';
import 'package:delayed_display/delayed_display.dart';
import 'package:app/core/core.dart';

class WelcomePage extends StatelessWidget {
  const WelcomePage({super.key});
  static Route<dynamic> route() {
    return MaterialPageRoute<void>(builder: (_) => const WelcomePage());
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Expanded(
                child: DelayedDisplay(
                  delay: Duration(milliseconds: 500),
                  fadeIn: true,
                  fadingDuration: Duration(milliseconds: 180),
                  slidingBeginOffset: Offset(0, 0.05),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Image.asset(
                        'assets/images/shared/logo.png',
                        height: 140,
                        width: 500,
                      ),
                      SizedBox(height: 60),
                      DelayedDisplay(
                        delay: Duration(milliseconds: 600),
                        child: SizedBox(
                          height: 50,
                          width: 200,
                          child: DefaultTextStyle(
                            style: TextStyle(
                              fontSize: 20,
                              letterSpacing: 2,
                              color: theme.colorScheme.onSurface,
                              fontWeight: FontWeight.w400,
                            ),
                            child: AnimatedTextKit(
                              repeatForever: true,
                              isRepeatingAnimation: true,
                              animatedTexts: [
                                TypewriterAnimatedText(
                                  '              ',
                                  textAlign: TextAlign.center,
                                  speed: Durations.short3,
                                ),
                                TypewriterAnimatedText(
                                  'A Touch Closer.\n',
                                  textAlign: TextAlign.center,
                                ),
                                TypewriterAnimatedText(
                                  'To Where you need to Go.\n',
                                  textAlign: TextAlign.center,
                                ),
                                TypewriterAnimatedText(
                                  'Anyplace.\n',
                                  textAlign: TextAlign.center,
                                ),
                                TypewriterAnimatedText(
                                  'Anytime.\n',
                                  textAlign: TextAlign.center,
                                ),
                                TypewriterAnimatedText(
                                  'Any Device.\n',
                                  textAlign: TextAlign.center,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              // Buttons at the bottom
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  spacing: 12,
                  // mainAxisSize: MainAxisSize.min,
                  children: [
                    AppButton.primary(
                      onPressed: () async {
                        if (context.mounted) {
                          Navigator.of(context).pushNamed('/signup');
                        }
                      },
                      text: 'GET STARTED',
                    ),
                    AppButton.tertiary(
                      onPressed: () async {
                        if (context.mounted) {
                          Navigator.of(context).pushNamed('/login');
                        }
                      },
                      text: 'I ALREADY HAVE AN ACCOUNT',
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
