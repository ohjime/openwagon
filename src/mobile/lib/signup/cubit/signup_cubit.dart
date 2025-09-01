import 'package:bloc/bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:app/core/repositories/authentication_repository.dart';

part 'signup_state.dart';

class SignupCubit extends Cubit<SignupState> {
  SignupCubit(this._authenticationRepository) : super(const SignupState());

  final AuthenticationRepository _authenticationRepository;

  Future<void> signup(String email, String password) async {
    emit(state.copyWith(status: SignupStatus.loading));
    try {
      await _authenticationRepository.signUp(email: email, password: password);
      emit(state.copyWith(status: SignupStatus.success));
    } on SignUpWithEmailAndPasswordFailure catch (e) {
      emit(
        state.copyWith(status: SignupStatus.failure, errorMessage: e.message),
      );
    } catch (e) {
      emit(
        state.copyWith(
          status: SignupStatus.failure,
          errorMessage: 'An unexpected error occurred',
        ),
      );
    }
  }

  Future<void> signupWithGoogle() async {
    emit(state.copyWith(status: SignupStatus.loading));
    try {
      await _authenticationRepository.logInWithGoogle();
    } catch (e) {
      emit(
        state.copyWith(
          status: SignupStatus.failure,
          errorMessage: e.toString(),
        ),
      );
    }
  }

  void resetError() {
    emit(state.copyWith(status: SignupStatus.initial, errorMessage: null));
  }
}
