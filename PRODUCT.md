# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Python + HTML/CSS; delegated to the implementation because no framework was requested.

## Users

Primary user: a student demonstrating a recommender system for a lab assignment. A prospective car buyer is the modeled end user of its recommendations.

## Product Purpose

Demonstrate how a recommender can suggest cars from a prefilled positive-preference matrix. The visitor enters practical vehicle parameters and sees matching cars ranked by co-preference PMI.

## Positioning

A small educational app that exposes item-to-item collaborative filtering using co-preference counts and PMI, grounded in the supplied recommender systems lab materials.

## Operating Context

The app is a local Python web app intended to be shared in a Git repository and run by a classmate while preparing a lab report.

## Capabilities and Constraints

The core recommender uses a prefilled buyer-car positive interaction matrix, item-to-item co-occurrence, and PMI-based ranking. The visitor enters up to eight vehicle parameters as catalog filters; the existing interaction matrix ranks matching cars. Demo interactions and listings are synthetic and must be labeled as such. The app should be small, readable, and require straightforward local setup.

## Brand Commitments

Use a simple, minimalist interface without generic AI-generated visual styling.

## Evidence on Hand

The repository contains the course lecture, lab instructions, and slides as PDFs. The lab explicitly allows an initiative topic and asks for implementation, analysis, interpretation, and a report. Demo vehicle records and interactions are not supplied and must be identified as synthetic.

## Product Principles

- Make the ranking method understandable to a student reviewing the code.
- Explain each recommendation using observable shared preferences.
- Label synthetic data and avoid implying real market coverage.
- Keep local setup simple for a classmate.
