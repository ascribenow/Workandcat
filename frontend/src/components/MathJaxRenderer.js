import React, { useEffect, useRef } from 'react';

const MathJaxRenderer = ({ children, className = "" }) => {
  const mathJaxRef = useRef(null);

  useEffect(() => {
    const renderMath = async () => {
      if (window.MathJax && mathJaxRef.current) {
        try {
          // Clear previous MathJax processing
          if (window.MathJax.typesetClear) {
            window.MathJax.typesetClear([mathJaxRef.current]);
          }
          
          // Process the MathJax content
          await window.MathJax.typesetPromise([mathJaxRef.current]);
          console.log('MathJax rendered successfully');
        } catch (err) {
          console.error('MathJax rendering error:', err);
        }
      } else if (!window.MathJax) {
        console.warn('MathJax not loaded yet, retrying in 1 second...');
        setTimeout(renderMath, 1000);
      }
    };

    renderMath();
  }, [children]);

  return (
    <div ref={mathJaxRef} className={`math-content ${className}`}>
      {children}
    </div>
  );
};

export default MathJaxRenderer;