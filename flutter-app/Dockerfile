# Stage 1: Build the Flutter web app
FROM ubuntu:20.04 AS flutter-builder

# Install dependencies
RUN apt-get update && \
    apt-get install -y curl git unzip xz-utils libglu1-mesa && \
    apt-get clean

# Setup Flutter environment
RUN mkdir -p /home/developer
WORKDIR /home/developer

# Download and setup Flutter
RUN git clone https://github.com/flutter/flutter.git -b stable --depth 1
ENV PATH="/home/developer/flutter/bin:${PATH}"

# Setup app directory
WORKDIR /home/developer/app

# Copy Flutter project files
COPY . .

# Create web directory if it doesn't exist
RUN mkdir -p web

# Copy web files
COPY index.html web/
COPY manifest.json web/

# Get Flutter packages
RUN flutter pub get

# Build the web app
RUN flutter build web --release

# Stage 2: Create the final image with Nginx to serve the Flutter web app
FROM nginx:alpine

# Copy the build output from the previous stage
COPY --from=flutter-builder /home/developer/app/build/web /usr/share/nginx/html

# Copy nginx configuration for routing API requests
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose the port
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]