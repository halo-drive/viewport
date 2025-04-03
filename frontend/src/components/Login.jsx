import React, { useState, useContext } from 'react';
import './Login.css';
import logoViolet from '../assets/logo-violet.png';
import { AuthContext } from '../AuthContext';

export default function Login() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSignup, setIsSignup] = useState(false);
  
  const { login, signup, loading, error } = useContext(AuthContext);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (isSignup) {
      if (!username || !email || !password) {
        alert('Please fill in all fields');
        return;
      }
      
      const result = await signup(username, email, password);
      if (result.success) {
        alert(result.message);
        setIsSignup(false); // Switch back to login
        setUsername('');
        setEmail('');
        setPassword('');
      }
    } else {
      if (!email || !password) {
        alert('Please fill in all fields');
        return;
      }
      
      await login(email, password);
    }
  };

  const togglePassword = () => {
    setShowPassword(!showPassword);
  };

  return (
    <div className="login-overlay">
      <form onSubmit={handleSubmit}>
        <div className="con">
          <header className="head-form">
            <img src={logoViolet} alt="Logo" className="login-logo" />
            <p>A POMO Robotics Venture</p>
          </header>
          
          {error && <div className="error-message">{error}</div>}
          
          <div className="field-set">
            {isSignup && (
              <>
                <span className="input-item">
                  <i className="fa fa-user-circle"></i>
                </span>
                <input 
                  className="form-input" 
                  id="txt-username" 
                  type="text" 
                  placeholder="Username" 
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required 
                />
                <br />
              </>
            )}
            
            <span className="input-item">
              <i className="fa fa-user-circle"></i>
            </span>
            <input 
              className="form-input" 
              id="txt-input" 
              type="text" 
              placeholder="Email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required 
            />
            
            <br />
            
            <span className="input-item">
              <i className="fa fa-key"></i>
            </span>
            <input 
              className="form-input" 
              type={showPassword ? "text" : "password"} 
              placeholder="Password" 
              id="pwd" 
              name="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required 
            />
            
            <span>
              <i 
                className={`fa ${showPassword ? "fa-eye-slash" : "fa-eye"}`} 
                aria-hidden="true" 
                id="eye" 
                onClick={togglePassword}
              ></i>
            </span>
            
            <br />
            
            <button type="submit" className="log-in" disabled={loading}> 
              {loading ? (isSignup ? "Signing up..." : "Logging in...") : (isSignup ? "Sign Up" : "Log In")}
            </button>
          </div>
          
          <div className="other">
            <button type="button" className="btn submits frgt-pass">Forgot Password</button>
            <button 
              type="button" 
              className="btn submits sign-up"
              onClick={() => setIsSignup(!isSignup)}
            >
              {isSignup ? "Back to Login" : "Sign Up"}
              {!isSignup && <i className="fa fa-user-plus" aria-hidden="true"></i>}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}