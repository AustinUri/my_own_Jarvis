plugins {
    id("com.android.application")
}

android {
    namespace = "com.jarvis.companion"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.jarvis.companion"
        minSdk = 28
        targetSdk = 35
        versionCode = 291
        versionName = "0.8-v29.1"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}


dependencies {
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
}
