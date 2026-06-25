# Use light-weight Nginx server
FROM nginx:alpine

# Copy custom Nginx configuration to override IPv6 default and add multi-port support
COPY default.conf /etc/nginx/conf.d/default.conf

# Copy static application files to Nginx web root
COPY index.html /usr/share/nginx/html/index.html
COPY questions.js /usr/share/nginx/html/questions.js
COPY questions.json /usr/share/nginx/html/questions.json

# Expose multiple HTTP ports to match any Coolify defaults
EXPOSE 80 3000 8080 5000

# Start Nginx server
CMD ["nginx", "-g", "daemon off;"]
