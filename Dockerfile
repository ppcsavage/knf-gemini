# Use light-weight Nginx server
FROM nginx:alpine

# Copy static application files to Nginx web root
COPY index.html /usr/share/nginx/html/index.html
COPY questions.js /usr/share/nginx/html/questions.js
COPY questions.json /usr/share/nginx/html/questions.json

# Expose HTTP port
EXPOSE 80

# Start Nginx server
CMD ["nginx", "-g", "daemon off;"]
